"""Raw-file storage backends.

local : filesystem (unit tests, single process)
db    : a table in the same Postgres (local clusters / docker-compose; no S3 needed)
s3    : Amazon S3 in EKS; credentials come from the pod's IAM role (IRSA)
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .db import Database

_SAFE = re.compile(r"[^A-Za-z0-9._-]")


def object_key(measurement_id: str, filename: str) -> str:
    safe = _SAFE.sub("_", os.path.basename(filename))[:100] or "upload.csv"
    return f"raw/{measurement_id}/{safe}"


class Storage(Protocol):
    def put(self, key: str, data: bytes) -> None: ...
    def get(self, key: str) -> bytes: ...


class LocalStorage:
    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if self.root not in p.parents:
            raise ValueError("invalid key")
        return p

    def put(self, key: str, data: bytes) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()


class DbStorage:
    def __init__(self, db: Database) -> None:
        self._db = db

    def put(self, key: str, data: bytes) -> None:
        from .db import RawObject

        with self._db.session() as s:
            s.merge(RawObject(key=key, data=data))
            s.commit()

    def get(self, key: str) -> bytes:
        from .db import RawObject

        with self._db.session() as s:
            obj = s.get(RawObject, key)
            if obj is None:
                raise KeyError(key)
            return obj.data


class S3Storage:
    def __init__(self, bucket: str, endpoint_url: str = "") -> None:
        import boto3

        # No credentials here on purpose: in EKS they come from the pod's IAM
        # role (IRSA). endpoint_url allows an S3-compatible store if needed.
        self._s3 = boto3.client("s3", endpoint_url=endpoint_url or None)
        self._bucket = bucket

    def put(self, key: str, data: bytes) -> None:
        self._s3.put_object(Bucket=self._bucket, Key=key, Body=data, ServerSideEncryption="AES256")

    def get(self, key: str) -> bytes:
        return self._s3.get_object(Bucket=self._bucket, Key=key)["Body"].read()


def make_storage(
    backend: str, path: str, bucket: str, endpoint_url: str, db: Database | None = None
) -> Storage:
    if backend == "local":
        return LocalStorage(path)
    if backend == "db":
        if db is None:
            raise ValueError("db storage needs a database")
        return DbStorage(db)
    if backend == "s3":
        if not bucket:
            raise ValueError("LABOPS_S3_BUCKET is required for s3 storage")
        return S3Storage(bucket, endpoint_url)
    raise ValueError(f"unknown storage backend: {backend}")

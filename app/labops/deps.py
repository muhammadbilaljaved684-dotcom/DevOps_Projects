"""Builds the shared dependencies (db, queue, storage) from settings.

Kept in one place so the APIs, the worker and the tests all wire things the
same way. Tests pass their own Deps instead of reading the environment.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import Settings, get_settings
from .db import Database
from .queue import Queue, make_queue
from .storage import Storage, make_storage


@dataclass
class Deps:
    settings: Settings
    db: Database
    queue: Queue
    storage: Storage


def build_deps(settings: Settings | None = None) -> Deps:
    s = settings or get_settings()
    db = Database(s.database_url)
    db.create_schema()
    return Deps(
        settings=s,
        db=db,
        queue=make_queue(s.queue_backend, s.redis_url, s.queue_name),
        storage=make_storage(s.storage_backend, s.storage_path, s.s3_bucket, s.s3_endpoint_url, db),
    )

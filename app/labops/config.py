"""Runtime configuration, read from environment variables.

Twelve-factor style: the same image runs locally, in CI and in Kubernetes;
only the environment changes. Values are read when get_settings() is called,
so tests can change the environment and get fresh settings.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # Database (SQLAlchemy URL). SQLite for local/tests, Postgres in clusters.
    database_url: str
    # Queue backend: "redis" or "memory" (memory = tests / single process).
    queue_backend: str
    redis_url: str
    queue_name: str
    # Raw-data storage: "local" or "s3". In AWS, S3 auth comes from IRSA /
    # EKS Pod Identity, so no access keys are ever configured.
    storage_backend: str
    storage_path: str
    s3_bucket: str
    s3_endpoint_url: str
    max_upload_bytes: int
    # Fault injection for game days (see docs/game-days.md):
    #   ""            normal
    #   "slow"        worker sleeps fault_delay_seconds per job
    #   "error"       worker fails every job
    #   "error-half"  worker fails ~50% of jobs
    fault_mode: str
    fault_delay_seconds: float
    worker_metrics_port: int
    worker_poll_timeout: int
    log_level: str


def get_settings() -> Settings:
    e = os.environ.get
    return Settings(
        database_url=e("LABOPS_DATABASE_URL", "sqlite:///./labops.db"),
        queue_backend=e("LABOPS_QUEUE_BACKEND", "memory"),
        redis_url=e("LABOPS_REDIS_URL", "redis://localhost:6379/0"),
        queue_name=e("LABOPS_QUEUE_NAME", "labops:jobs"),
        storage_backend=e("LABOPS_STORAGE_BACKEND", "local"),
        storage_path=e("LABOPS_STORAGE_PATH", "./data"),
        s3_bucket=e("LABOPS_S3_BUCKET", ""),
        s3_endpoint_url=e("LABOPS_S3_ENDPOINT_URL", ""),
        max_upload_bytes=int(e("LABOPS_MAX_UPLOAD_BYTES", str(5 * 1024 * 1024))),
        fault_mode=e("LABOPS_FAULT_MODE", ""),
        fault_delay_seconds=float(e("LABOPS_FAULT_DELAY_SECONDS", "45")),
        worker_metrics_port=int(e("LABOPS_WORKER_METRICS_PORT", "9100")),
        worker_poll_timeout=int(e("LABOPS_WORKER_POLL_TIMEOUT", "5")),
        log_level=e("LABOPS_LOG_LEVEL", "INFO"),
    )

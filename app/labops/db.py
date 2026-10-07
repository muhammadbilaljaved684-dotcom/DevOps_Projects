"""Persistence: one table of measurements and their analysis results."""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Enum, Float, LargeBinary, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Status(enum.StrEnum):
    queued = "queued"
    processing = "processing"
    done = "done"
    failed = "failed"


class RawObject(Base):
    """Raw uploads when storage_backend=db (local clusters without S3)."""

    __tablename__ = "raw_objects"

    key: Mapped[str] = mapped_column(String(512), primary_key=True)
    data: Mapped[bytes] = mapped_column(LargeBinary)


class Measurement(Base):
    __tablename__ = "measurements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(512))
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.queued, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "filename": self.filename,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "processing_seconds": self.processing_seconds,
            "result": self.result,
            "error": self.error,
        }


class Database:
    def __init__(self, url: str):
        # CloudNativePG publishes plain postgresql:// URIs; we use psycopg 3.
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://") :]
        kwargs = {"pool_pre_ping": True}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        self.engine = create_engine(url, **kwargs)
        self._sessions = sessionmaker(self.engine, expire_on_commit=False)

    def create_schema(self) -> None:
        # For a demo project create_all is enough; a real service would use
        # Alembic migrations run as a pre-sync Argo CD hook.
        Base.metadata.create_all(self.engine)

    def session(self) -> Session:
        return self._sessions()

    def close(self) -> None:
        """Release pooled connections (on shutdown, and between tests)."""
        self.engine.dispose()

    def ping(self) -> bool:
        with self.engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        return True

    def get(self, measurement_id: str) -> Measurement | None:
        with self.session() as s:
            return s.get(Measurement, measurement_id)

    def latest(self, limit: int = 50) -> list[Measurement]:
        with self.session() as s:
            stmt = select(Measurement).order_by(Measurement.created_at.desc()).limit(limit)
            return list(s.scalars(stmt))

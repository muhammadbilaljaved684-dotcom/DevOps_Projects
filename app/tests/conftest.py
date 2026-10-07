import pytest

from labops.config import get_settings
from labops.db import Database
from labops.deps import Deps
from labops.queue import MemoryQueue
from labops.storage import LocalStorage


@pytest.fixture
def deps(tmp_path, monkeypatch):
    monkeypatch.setenv("LABOPS_DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("LABOPS_STORAGE_PATH", str(tmp_path / "data"))
    settings = get_settings()
    db = Database(settings.database_url)
    db.create_schema()
    yield Deps(settings=settings, db=db, queue=MemoryQueue(), storage=LocalStorage(settings.storage_path))
    db.close()

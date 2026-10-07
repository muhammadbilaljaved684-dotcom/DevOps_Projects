import pytest

from labops.queue import Job, MemoryQueue, make_queue
from labops.storage import LocalStorage, make_storage, object_key


def test_object_key_is_sanitised():
    assert object_key("abc", "../../etc/passwd") == "raw/abc/passwd"
    assert object_key("abc", "my file (1).csv") == "raw/abc/my_file__1_.csv"
    assert object_key("abc", "") == "raw/abc/upload.csv"


def test_local_storage_roundtrip_and_traversal(tmp_path):
    s = LocalStorage(str(tmp_path))
    s.put("raw/x/a.csv", b"hello")
    assert s.get("raw/x/a.csv") == b"hello"
    with pytest.raises(ValueError):
        s.put("../escape", b"x")


def test_db_storage_roundtrip(deps):
    s = make_storage("db", "", "", "", deps.db)
    s.put("raw/a/b.csv", b"one")
    s.put("raw/a/b.csv", b"two")  # overwrite is idempotent
    assert s.get("raw/a/b.csv") == b"two"
    with pytest.raises(KeyError):
        s.get("missing")
    with pytest.raises(ValueError):
        make_storage("db", "", "", "", None)


def test_build_deps_from_env(tmp_path, monkeypatch):
    from labops.deps import build_deps

    monkeypatch.setenv("LABOPS_DATABASE_URL", f"sqlite:///{tmp_path}/x.db")
    monkeypatch.setenv("LABOPS_STORAGE_BACKEND", "db")
    d = build_deps()
    d.storage.put("k", b"v")
    assert d.storage.get("k") == b"v"
    d.db.close()


def test_memory_queue_fifo():
    q = MemoryQueue()
    q.put("a")
    q.put("b")
    assert q.depth() == 2
    assert q.get().measurement_id == "a"
    assert q.get().measurement_id == "b"
    assert q.get() is None


def test_job_serialisation():
    j = Job("id1", 123.5)
    assert Job.loads(j.dumps()) == j


def test_factories_reject_unknown():
    with pytest.raises(ValueError):
        make_queue("kafka", "", "")
    with pytest.raises(ValueError):
        make_storage("ftp", "", "", "")
    with pytest.raises(ValueError):
        make_storage("s3", "", "", "")

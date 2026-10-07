"""End-to-end: upload through ingest API, process with worker, read via results API."""

import time

import pytest
from fastapi.testclient import TestClient

from labops import ingest_api, results_api, worker
from labops.analysis import synthetic_spectrum
from labops.db import Status
from labops.queue import Job


def upload(client, data, name="s.csv"):
    return client.post("/api/v1/uploads", files={"file": (name, data, "text/csv")})


def test_full_flow(deps):
    with TestClient(ingest_api.create_app(deps)) as ingest, TestClient(results_api.create_app(deps)) as res:
        r = upload(ingest, synthetic_spectrum(field_tesla=2e-3))
        assert r.status_code == 202
        mid = r.json()["id"]
        assert deps.queue.depth() == 1

        assert worker.process(deps, deps.queue.get()) == Status.done

        body = res.get(f"/api/v1/measurements/{mid}").json()
        assert body["status"] == "done"
        assert body["result"]["field_tesla"] == pytest.approx(2e-3, rel=0.03)

        listing = res.get("/api/v1/measurements").json()
        assert [m["id"] for m in listing] == [mid]
        assert "LabOps measurements" in res.get("/").text
        assert res.get("/api/v1/measurements/nope").status_code == 404


def test_rejects_invalid_and_oversized(deps, monkeypatch):
    with TestClient(ingest_api.create_app(deps)) as c:
        assert upload(c, b"not,a\nspectrum\n").status_code == 422

    monkeypatch.setenv("LABOPS_MAX_UPLOAD_BYTES", "100")
    from labops.config import get_settings

    small = type(deps)(settings=get_settings(), db=deps.db, queue=deps.queue, storage=deps.storage)
    with TestClient(ingest_api.create_app(small)) as c:
        assert upload(c, synthetic_spectrum()).status_code == 413
    assert deps.queue.depth() == 0


def test_health_and_metrics(deps):
    with TestClient(ingest_api.create_app(deps)) as c:
        assert c.get("/healthz").text == "ok"
        assert c.get("/readyz").text == "ready"
        assert "labops_uploads_total" in c.get("/metrics").text
    with TestClient(results_api.create_app(deps)) as c:
        assert c.get("/readyz").status_code == 200
        assert "labops_job_e2e_seconds" in c.get("/metrics").text


def test_readyz_fails_when_queue_down(deps):
    class Broken:
        def ping(self):
            raise ConnectionError("redis down")

    deps.queue = Broken()
    with TestClient(ingest_api.create_app(deps)) as c:
        assert c.get("/healthz").status_code == 200  # liveness must not depend on redis
        assert c.get("/readyz").status_code == 503


@pytest.mark.parametrize("mode", ["error"])
def test_fault_injection_marks_job_failed(deps, monkeypatch, mode):
    monkeypatch.setenv("LABOPS_FAULT_MODE", mode)
    from labops.config import get_settings

    deps.settings = get_settings()
    with TestClient(ingest_api.create_app(deps)) as c:
        upload(c, synthetic_spectrum())
    assert worker.process(deps, deps.queue.get()) == Status.failed


def test_slow_fault_delays_processing(deps, monkeypatch):
    monkeypatch.setenv("LABOPS_FAULT_MODE", "slow")
    monkeypatch.setenv("LABOPS_FAULT_DELAY_SECONDS", "0.2")
    from labops.config import get_settings

    deps.settings = get_settings()
    with TestClient(ingest_api.create_app(deps)) as c:
        upload(c, synthetic_spectrum())
    t = time.monotonic()
    assert worker.process(deps, deps.queue.get()) == Status.done
    assert time.monotonic() - t >= 0.2


def test_unknown_measurement_job(deps):
    assert worker.process(deps, Job("missing", time.time())) == Status.failed


def test_worker_run_loop(deps, monkeypatch):
    monkeypatch.setattr(worker, "start_http_server", lambda port: None)
    with TestClient(ingest_api.create_app(deps)) as c:
        for i in range(3):
            upload(c, synthetic_spectrum(seed=i), name=f"{i}.csv")
    assert worker.run(deps, max_jobs=3) == 3
    assert all(m.status == Status.done for m in deps.db.latest())

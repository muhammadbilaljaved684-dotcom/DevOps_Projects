from datetime import timedelta

from fastapi.testclient import TestClient

from labops import cli, ingest_api, worker
from labops.analysis import synthetic_spectrum
from labops.db import Measurement, Status, utcnow


def test_generate_writes_valid_csv(tmp_path, capsys):
    out = tmp_path / "s.csv"
    cli.main(["generate", "--field-mt", "1.5", "-o", str(out)])
    assert out.read_text().startswith("frequency_hz,intensity")
    cli.main(["generate"])
    assert "frequency_hz" in capsys.readouterr().out


def test_requeue_only_old_stuck_jobs(deps):
    with TestClient(ingest_api.create_app(deps)) as c:
        for i in range(3):
            c.post("/api/v1/uploads", files={"file": (f"{i}.csv", synthetic_spectrum(seed=i), "text/csv")})
    # Simulate losing the queue: drain it without processing.
    while deps.queue.get():
        pass
    with deps.db.session() as s:
        rows = s.query(Measurement).order_by(Measurement.filename).all()
        rows[0].created_at = utcnow() - timedelta(minutes=10)
        rows[1].created_at = utcnow() - timedelta(minutes=10)
        rows[1].status = Status.done
        s.commit()
        old_stuck = rows[0].id

    assert cli.requeue_stuck(deps, 300, dry_run=True) == [old_stuck]
    assert deps.queue.depth() == 0
    assert cli.requeue_stuck(deps, 300) == [old_stuck]
    assert worker.process(deps, deps.queue.get()) == Status.done

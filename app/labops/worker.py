"""worker: pull jobs, fit spectra, store results, emit SLI metrics."""

from __future__ import annotations

import logging
import random
import signal
import time

from prometheus_client import start_http_server

from .analysis import SpectrumError, analyse, parse_csv
from .db import Measurement, Status, utcnow
from .deps import Deps, build_deps
from .logging_setup import setup_logging
from .metrics import FAULT_MODE, JOB_E2E, JOB_PROCESSING, JOBS, QUEUE_DEPTH
from .queue import Job

log = logging.getLogger("labops.worker")


class FaultInjected(RuntimeError):
    pass


def _apply_fault(mode: str, delay: float) -> None:
    if mode == "slow":
        time.sleep(delay)
    elif mode == "error":
        raise FaultInjected("fault injection: error")
    elif mode == "error-half" and random.random() < 0.5:  # noqa: S311 - not crypto
        raise FaultInjected("fault injection: error-half")


def process(deps: Deps, job: Job) -> Status:
    """Process one job. Returns the final status. Never raises."""
    s = deps.settings
    started = time.monotonic()
    with deps.db.session() as session:
        m = session.get(Measurement, job.measurement_id)
        if m is None:
            log.warning("job for unknown measurement", extra={"measurement_id": job.measurement_id})
            JOBS.labels("unknown").inc()
            return Status.failed
        m.status = Status.processing
        session.commit()

        try:
            _apply_fault(s.fault_mode, s.fault_delay_seconds)
            x, y = parse_csv(deps.storage.get(m.storage_key))
            m.result = analyse(x, y).to_dict()
            m.status = Status.done
            outcome = "success"
        except (SpectrumError, FaultInjected) as exc:
            m.status, m.error, outcome = Status.failed, str(exc), "failed"
        except Exception as exc:  # noqa: BLE001 - a bad file must not kill the worker
            log.exception("unexpected error", extra={"measurement_id": m.id})
            m.status, m.error, outcome = Status.failed, f"internal error: {exc}", "error"

        elapsed = time.monotonic() - started
        m.finished_at = utcnow()
        m.processing_seconds = elapsed
        session.commit()

    JOBS.labels(outcome).inc()
    JOB_PROCESSING.observe(elapsed)
    JOB_E2E.labels(outcome).observe(max(0.0, time.time() - job.enqueued_at))
    log.info(
        "job finished",
        extra={"measurement_id": job.measurement_id, "outcome": outcome, "duration_s": round(elapsed, 3)},
    )
    return m.status


def run(deps: Deps | None = None, max_jobs: int | None = None) -> int:
    deps = deps or build_deps()
    s = deps.settings
    setup_logging(s.log_level)
    FAULT_MODE.labels(s.fault_mode or "none").set(1 if s.fault_mode else 0)
    if s.fault_mode:
        log.warning("FAULT INJECTION ACTIVE: %s", s.fault_mode)

    stopping = False

    def _stop(*_: object) -> None:
        nonlocal stopping
        stopping = True
        log.info("shutdown requested, finishing current job")

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    start_http_server(s.worker_metrics_port)
    log.info("worker started", extra={"role": "worker"})

    done = 0
    while not stopping and (max_jobs is None or done < max_jobs):
        try:
            QUEUE_DEPTH.set(deps.queue.depth())
            job = deps.queue.get(timeout=s.worker_poll_timeout)
        except Exception:  # noqa: BLE001 - queue blips: back off, don't crash
            log.exception("queue error, retrying in 2s")
            time.sleep(2)
            continue
        if job is None:
            continue
        process(deps, job)
        done += 1
    return done


def main() -> None:
    run()


if __name__ == "__main__":
    main()

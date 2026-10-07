"""Small operations CLI.

python -m labops.cli generate --field-mt 2.0 -o sample.csv
python -m labops.cli load --url http://localhost:8000 --count 200 --rate 5
python -m labops.cli requeue --older-than 300          # runbook: stuck jobs
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import timedelta

import httpx
from sqlalchemy import select

from .analysis import synthetic_spectrum
from .db import Measurement, Status, utcnow
from .deps import Deps, build_deps


def cmd_generate(args: argparse.Namespace) -> None:
    data = synthetic_spectrum(field_tesla=args.field_mt / 1e3, seed=args.seed)
    if args.output == "-":
        sys.stdout.write(data.decode())
    else:
        with open(args.output, "wb") as fh:
            fh.write(data)


def cmd_load(args: argparse.Namespace) -> None:
    ok = fail = 0
    interval = 1.0 / args.rate if args.rate > 0 else 0
    with httpx.Client(base_url=args.url, timeout=10) as client:
        for i in range(args.count):
            data = synthetic_spectrum(field_tesla=(1 + (i % 5)) / 1e3, seed=i)
            r = client.post("/api/v1/uploads", files={"file": (f"load-{i}.csv", data, "text/csv")})
            ok, fail = (ok + 1, fail) if r.status_code == 202 else (ok, fail + 1)
            if interval:
                time.sleep(interval)
    print(f"sent={args.count} accepted={ok} failed={fail}")


def requeue_stuck(deps: Deps, older_than_seconds: int, dry_run: bool = False) -> list[str]:
    """Re-enqueue measurements stuck in queued/processing (e.g. after losing
    the Redis pod or a worker dying mid-job). Safe to run repeatedly: the
    worker simply re-processes and overwrites the result."""
    cutoff = utcnow() - timedelta(seconds=older_than_seconds)
    with deps.db.session() as s:
        stmt = select(Measurement.id, Measurement.created_at).where(
            Measurement.status.in_([Status.queued, Status.processing])
        )
        ids = []
        for mid, created in s.execute(stmt):
            # SQLite returns naive datetimes; treat them as UTC.
            if created.tzinfo is None:
                created = created.replace(tzinfo=cutoff.tzinfo)
            if created < cutoff:
                ids.append(mid)
    if not dry_run:
        for mid in ids:
            deps.queue.put(mid)
    return ids


def cmd_requeue(args: argparse.Namespace) -> None:
    ids = requeue_stuck(build_deps(), args.older_than, args.dry_run)
    verb = "would requeue" if args.dry_run else "requeued"
    print(f"{verb} {len(ids)} measurement(s)")
    for mid in ids:
        print(f"  {mid}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="labops")
    sub = p.add_subparsers(required=True)

    g = sub.add_parser("generate", help="write a synthetic ODMR spectrum as CSV")
    g.add_argument("--field-mt", type=float, default=2.0)
    g.add_argument("--seed", type=int, default=0)
    g.add_argument("-o", "--output", default="-")
    g.set_defaults(func=cmd_generate)

    lo = sub.add_parser("load", help="send synthetic uploads to an ingest API")
    lo.add_argument("--url", required=True)
    lo.add_argument("--count", type=int, default=100)
    lo.add_argument("--rate", type=float, default=5.0, help="uploads per second")
    lo.set_defaults(func=cmd_load)

    rq = sub.add_parser("requeue", help="re-enqueue jobs stuck in queued/processing")
    rq.add_argument("--older-than", type=int, default=300, help="seconds")
    rq.add_argument("--dry-run", action="store_true")
    rq.set_defaults(func=cmd_requeue)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

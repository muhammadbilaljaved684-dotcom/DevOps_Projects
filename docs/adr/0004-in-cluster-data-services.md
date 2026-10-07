# ADR 0004: Postgres via CloudNativePG, Redis in-cluster

**Status:** accepted

## Context
Managed services (RDS, ElastiCache, SQS) remove operational work but add cost and make the local `kind` environment differ from prod.

## Decision
- **Postgres:** CloudNativePG operator. Two instances in prod with automatic failover, continuous WAL archiving to S3 (point-in-time recovery), daily base backups. Same manifests run on kind.
- **Redis:** a single pod with AOF persistence, used only as a job queue.
- **Raw files:** S3 in prod (IRSA), a Postgres table in dev (no S3 emulator needed).

## Consequences
- Identical topology locally and in AWS; database failover can be rehearsed for free (game day 3).
- I operate Postgres myself: upgrades, storage, backups. That's the trade-off, and it's documented in the runbooks.
- Losing the Redis pod loses queued jobs. The database still knows they're `queued`, and `labops requeue` re-enqueues them (runbook: queue-backlog). **SQS** would remove this failure mode and is the first thing I'd change.

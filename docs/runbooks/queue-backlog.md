# Runbook: LabOpsQueueBacklog (and "jobs stuck in queued")

**Meaning:** more than 100 jobs have been waiting for 10 minutes. Results are delayed; the SLO alert usually follows.

## Check

```bash
NS=labops-prod
kubectl -n $NS get deploy labops-worker labops-redis
kubectl -n $NS get hpa labops-worker
kubectl -n $NS logs deploy/labops-worker --since=10m | tail -20
```

| Observation | Action |
|---|---|
| Workers running, CPU near limit, HPA at max | Real load spike: raise `maxReplicas` (PR), check node capacity |
| Workers logging "queue error" | Redis unreachable → check the Redis pod and the NetworkPolicy |
| Workers 0/N ready | See [workers-down](workers-down.md) |
| Queue depth is 0 but measurements stay `queued` | Redis lost its data (pod rescheduled) → requeue, below |

## Requeue stuck jobs

Jobs are recorded in Postgres before they're queued, so nothing is lost when Redis is. Re-enqueue anything stuck for more than 5 minutes:

```bash
kubectl -n $NS exec deploy/labops-ingest -- python -m labops.cli requeue --older-than 300 --dry-run
kubectl -n $NS exec deploy/labops-ingest -- python -m labops.cli requeue --older-than 300
```
It's idempotent: a job processed twice just overwrites its own result.

## Prevent

The durable fix is a managed queue (SQS with a dead-letter queue); see ADR 0004.

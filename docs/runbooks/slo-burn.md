# Runbook: LabOpsSLOFastBurn / LabOpsSLOSlowBurn / LabOpsSLOBudgetLeak

**Meaning:** too many uploads are failing or taking longer than 30 s. Users (lab staff) are waiting for results.

## 1. Triage (5 minutes)

1. Grafana → **LabOps** dashboard. Which is it?
   - *Jobs per second by outcome* shows `failed`/`error` → **failures**, go to 2a.
   - Latency p95/p99 above 30 s, outcomes mostly `success` → **slowness**, go to 2b.
2. Did something change? Argo CD → `labops-<env>` → History. A sync in the last hour is the prime suspect.
3. Is fault injection on? The *Fault injection* stat shows `ACTIVE` → a game day is running, or someone left it on.

## 2a. Failures

```bash
NS=labops-prod
kubectl -n $NS logs deploy/labops-worker --since=15m | jq -r 'select(.outcome!="success") | .msg + " " + (.measurement_id//"")' | sort | uniq -c | sort -rn | head
```
- Same error for every job after a recent deploy → **roll back** (step 3).
- `SpectrumError` for one uploader → a bad instrument file format; not a platform fault. Check `failed/` on the lab-edge server.
- Database errors → check `kubectl -n $NS get cluster.postgresql.cnpg.io` (phase should be healthy).

## 2b. Slowness

```bash
kubectl -n $NS get hpa labops-worker
kubectl -n $NS top pods -l app.kubernetes.io/component=worker
```
- HPA at max replicas and CPU high → raise `autoscaling.worker.maxReplicas` via a PR, or check whether nodes can fit more pods (`kubectl get nodes`, pending pods).
- Queue depth growing but workers idle → workers can't reach Redis; see [workers-down](workers-down.md).

## 3. Roll back

```bash
git log --oneline -5 -- deploy/helm/labops/values-prod.yaml
git revert <sha-of-bad-deploy> && git push
```
Prod has a sync window; for incidents, sync manually in Argo CD (manual sync is allowed in the window config).

## 4. Afterwards

Write a postmortem from [the template](../postmortems/TEMPLATE.md) within two working days, even if the cause was obvious.

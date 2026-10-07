# Runbook: restore data

Pick the smallest tool that solves the problem.

## A. Bad data written, database otherwise fine → point-in-time recovery

CloudNativePG archives WAL to S3 continuously, so you can restore to any moment. Create a **new** cluster recovered to just before the incident, check it, then switch the app to it.

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: labops-pg-restore
  namespace: labops-prod
spec:
  instances: 2
  storage: { size: 10Gi, storageClass: gp3 }
  bootstrap:
    recovery:
      source: labops-pg
      recoveryTarget:
        targetTime: "2026-01-01 10:59:00+00"   # just before the incident
  externalClusters:
    - name: labops-pg
      barmanObjectStore:
        destinationPath: s3://<backup-bucket>/cnpg
        s3Credentials: { inheritFromIAMRole: true }
```
Then point `database.existingSecret` at `labops-pg-restore-app` (PR), verify, and retire the old cluster.

## B. Whole namespace gone → Velero

```bash
velero backup get
velero restore create --from-backup <backup-name> --wait
```
Pause Argo CD auto-sync for `root` and `labops-prod` first, or it will race the restore. `chaos/gameday-4-restore-drill.sh` scripts and times this.

## C. Raw upload files

S3 has the originals under `raw/<measurement-id>/`. Results can always be recomputed from them by re-queuing (`labops requeue`), so the raw bucket is the true source of record.

#!/usr/bin/env bash
# GAME DAY 3 - kill the Postgres primary.
# Hypothesis: CloudNativePG promotes the replica within ~30 s; readiness
# probes take app pods out of rotation during the switch; no data is lost.
# Needs postgres.instances >= 2 (prod values, or --set postgres.instances=2).
set -euo pipefail
NS="${NS:-labops-dev}"
CLUSTER="${CLUSTER:-labops-pg}"

PRIMARY=$(kubectl -n "$NS" get cluster.postgresql.cnpg.io "$CLUSTER" -o jsonpath='{.status.currentPrimary}')
echo "Primary is $PRIMARY. Deleting it at $(date -u +%T)"
kubectl -n "$NS" delete pod "$PRIMARY" --wait=false

for _ in $(seq 1 30); do
  NOW=$(kubectl -n "$NS" get cluster.postgresql.cnpg.io "$CLUSTER" -o jsonpath='{.status.currentPrimary}')
  PHASE=$(kubectl -n "$NS" get cluster.postgresql.cnpg.io "$CLUSTER" -o jsonpath='{.status.phase}')
  echo "$(date -u +%T)  primary=$NOW  phase=$PHASE"
  [[ "$NOW" != "$PRIMARY" && "$PHASE" == "Cluster in healthy state" ]] && break
  sleep 3
done
echo "Check the results API still lists every measurement uploaded before the failover."

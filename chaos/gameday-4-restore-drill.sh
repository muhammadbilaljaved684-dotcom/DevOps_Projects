#!/usr/bin/env bash
# GAME DAY 4 - disaster recovery drill (EKS/prod only).
# Delete the whole prod namespace, restore it from the latest Velero backup,
# and time it. The number you get is your real RTO; put it in the README.
set -euo pipefail
NS=labops-prod

read -r -p "This DELETES namespace $NS. Type the namespace name to continue: " ok
[[ "$ok" == "$NS" ]] || { echo "aborted"; exit 1; }

BACKUP=$(velero backup get -o json | jq -r \
  '[.items[] | select(.status.phase=="Completed")] | sort_by(.status.completionTimestamp) | last | .metadata.name')
echo "Latest good backup: $BACKUP"

# Argo CD would immediately recreate the app; pause it (and the root app that
# would self-heal it back) so we test Velero, not Argo.
for app in root labops-prod; do
  kubectl -n argocd patch application "$app" --type merge -p '{"spec":{"syncPolicy":null}}'
done

START=$(date +%s)
kubectl delete namespace "$NS" --wait=true
velero restore create "drill-$(date +%Y%m%d-%H%M)" --from-backup "$BACKUP" --wait
kubectl -n "$NS" wait --for=condition=available deploy --all --timeout=15m
END=$(date +%s)

echo "RESTORE COMPLETE in $(( (END - START) / 60 )) min $(( (END - START) % 60 )) s"
echo "Re-enable GitOps: kubectl apply -n argocd -f deploy/argocd/root.yaml"
echo "Note: Velero restores the Postgres volumes; if CloudNativePG refuses to start"
echo "from them, recover from its own S3 backup instead (docs/runbooks/restore.md)."
echo "Finding that out during a drill, not an outage, is the point."

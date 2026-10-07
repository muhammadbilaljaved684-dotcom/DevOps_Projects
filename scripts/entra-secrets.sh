#!/usr/bin/env bash
# Load the Entra ID SSO client secrets (from Terraform state) into the
# cluster as Kubernetes Secrets. Secrets go straight from state to the
# cluster: they are never written to disk or committed to Git.
set -euo pipefail
cd "$(dirname "$0")/.."
TF="terraform -chdir=infra/terraform/envs/entra"

TENANT=$($TF output -raw tenant_id)
ADMINS=$($TF output -raw admins_group_id)
DEVS=$($TF output -raw developers_group_id)
GRAFANA_ID=$($TF output -json client_ids | jq -r .grafana)
GRAFANA_SECRET=$($TF output -json client_secrets | jq -r .grafana)
ARGOCD_SECRET=$($TF output -json client_secrets | jq -r .argocd)

kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
kubectl -n monitoring create secret generic grafana-entra \
  --from-literal=ENTRA_SSO_ENABLED=true \
  --from-literal=ENTRA_TENANT_ID="$TENANT" \
  --from-literal=ENTRA_CLIENT_ID="$GRAFANA_ID" \
  --from-literal=ENTRA_CLIENT_SECRET="$GRAFANA_SECRET" \
  --from-literal=ENTRA_ADMINS_GROUP="$ADMINS" \
  --from-literal=ENTRA_DEVS_GROUP="$DEVS" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n argocd create secret generic argocd-entra \
  --from-literal=clientSecret="$ARGOCD_SECRET" \
  --dry-run=client -o yaml | kubectl label --local -f - app.kubernetes.io/part-of=argocd -o yaml \
  | kubectl apply -f -

kubectl -n monitoring rollout restart deploy -l app.kubernetes.io/name=grafana || true
echo "Done. Put these IDs into deploy/argocd/install/values-entra.yaml:"
echo "  TENANT_ID=$TENANT  ARGOCD_CLIENT_ID=$($TF output -json client_ids | jq -r .argocd)"
echo "  ENTRA_ADMINS_GROUP_ID=$ADMINS  ENTRA_DEVS_GROUP_ID=$DEVS"

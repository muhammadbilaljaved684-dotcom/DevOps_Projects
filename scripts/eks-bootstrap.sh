#!/usr/bin/env bash
# After `terraform apply` in infra/terraform/envs/aws: connect to the cluster,
# install Argo CD, and hand everything else over to GitOps.
set -euo pipefail
cd "$(dirname "$0")/.."

REGION="${AWS_REGION:-eu-central-1}"
TF_DIR=infra/terraform/envs/aws

CLUSTER=$(terraform -chdir="$TF_DIR" output -raw cluster_name)
aws eks update-kubeconfig --region "$REGION" --name "$CLUSTER"

kubectl apply -f deploy/platform/storageclass-gp3.yaml
# The EKS default gp2 class must not stay default alongside gp3.
kubectl annotate storageclass gp2 storageclass.kubernetes.io/is-default-class=false --overwrite || true

helm repo add argo https://argoproj.github.io/argo-helm >/dev/null
EXTRA=()
[[ "${ENTRA:-0}" == "1" ]] && EXTRA=(-f deploy/argocd/install/values-entra.yaml)
helm upgrade --install argocd argo/argo-cd -n argocd --create-namespace \
  --version 10.10.0 -f deploy/argocd/install/values.yaml "${EXTRA[@]}" --wait

kubectl apply -n argocd -f deploy/argocd/root.yaml
kubectl apply -n argocd -f deploy/argocd/apps-prod-only/

cat <<EOF

Argo CD is syncing the platform. Fill these Terraform outputs into Git:
  values-prod.yaml  serviceAccount.annotations  <- $(terraform -chdir="$TF_DIR" output -raw labops_irsa_role_arn)
  values-prod.yaml  postgres.backup.roleArn     <- $(terraform -chdir="$TF_DIR" output -raw pg_role_arn)
  values-prod.yaml  config.s3Bucket             <- $(terraform -chdir="$TF_DIR" output -raw raw_bucket_name)
  backup bucket (values-prod + velero.yaml)     <- $(terraform -chdir="$TF_DIR" output -raw backup_bucket_name)
  velero.yaml role-arn                          <- $(terraform -chdir="$TF_DIR" output -raw velero_role_arn)
EOF

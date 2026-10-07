#!/usr/bin/env bash
# Free local environment on kind: same Helm chart as EKS, minus cloud bits.
#   ./scripts/local-up.sh            # app only (fast, ~3 min)
#   ./scripts/local-up.sh --gitops   # + Argo CD, monitoring, Kyverno from Git
set -euo pipefail
cd "$(dirname "$0")/.."

GITOPS=false
[[ "${1:-}" == "--gitops" ]] && GITOPS=true

need() { command -v "$1" >/dev/null || { echo "missing: $1"; exit 1; }; }
for t in docker kind kubectl helm; do need "$t"; done

if ! kind get clusters | grep -qx labops; then
  kind create cluster --config deploy/kind/kind-config.yaml
fi
kubectl config use-context kind-labops >/dev/null

echo ">> building app image and loading it into kind"
docker build -t labops:dev app
kind load docker-image labops:dev --name labops

echo ">> CloudNativePG operator"
helm repo add cnpg https://cloudnative-pg.github.io/charts >/dev/null
helm upgrade --install cnpg cnpg/cloudnative-pg -n cnpg-system --create-namespace \
  --version 0.29.1 --wait

if $GITOPS; then
  echo ">> Argo CD (then everything else comes from Git)"
  helm repo add argo https://argoproj.github.io/argo-helm >/dev/null
  helm upgrade --install argocd argo/argo-cd -n argocd --create-namespace \
    --version 10.10.0 -f deploy/argocd/install/values.yaml --wait
  kubectl apply -n argocd -f deploy/argocd/root.yaml
  echo "Argo CD admin password:"
  kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo
  echo "kubectl -n argocd port-forward svc/argocd-server 8080:80   ->  http://localhost:8080"
  exit 0
fi

echo ">> LabOps chart (local image, no monitoring CRDs, no gateway)"
kubectl create namespace labops-dev --dry-run=client -o yaml | kubectl apply -f - >/dev/null
kubectl label namespace labops-dev --overwrite \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/enforce-version=latest >/dev/null
helm upgrade --install labops deploy/helm/labops -n labops-dev --create-namespace \
  -f deploy/helm/labops/values.yaml -f deploy/helm/labops/values-dev.yaml \
  --set image.repository=labops --set image.tag=dev \
  --set monitoring.serviceMonitor=false --set monitoring.prometheusRule=false \
  --set gateway.enabled=false --wait --timeout 10m

kubectl -n labops-dev get pods
cat <<'EOF'

Ready. In two terminals:
  kubectl -n labops-dev port-forward svc/labops-ingest 8000:8000
  kubectl -n labops-dev port-forward svc/labops-results 8001:8000
Then:  make demo   and open http://localhost:8001
EOF

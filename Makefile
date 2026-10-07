# LabOps - one entry point for everything. `make help` lists targets.
SHELL := /bin/bash
.DEFAULT_GOAL := help
TF_AWS := infra/terraform/envs/aws

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n",$$1,$$2}'

##@ App
.PHONY: test lint dev demo load
test: ## Run unit + integration tests with coverage gate
	cd app && pytest

lint: ## Lint Python, Helm, shell
	cd app && ruff check . && ruff format --check .
	helm lint deploy/helm/labops -f deploy/helm/labops/values.yaml -f deploy/helm/labops/values-dev.yaml
	shellcheck scripts/*.sh chaos/*.sh

dev: ## Run the full stack locally with docker compose
	docker compose up --build -d
	@echo "ingest: http://localhost:8000/docs   results: http://localhost:8001"

demo: ## Send 20 synthetic spectra to localhost:8000
	cd app && python -m labops.cli load --url http://localhost:8000 --count 20 --rate 4

load: ## Steady background load for game days (Ctrl-C to stop)
	cd app && python -m labops.cli load --url http://localhost:8000 --count 100000 --rate 2

##@ Local Kubernetes (kind, free)
.PHONY: kind-up kind-gitops kind-down
kind-up: ## kind cluster + CloudNativePG + LabOps chart
	./scripts/local-up.sh

kind-gitops: ## kind cluster + Argo CD managing everything from Git
	./scripts/local-up.sh --gitops

kind-down: ## Delete the kind cluster
	kind delete cluster --name labops

##@ AWS (costs money - destroy when done)
.PHONY: tf-init tf-plan tf-apply eks-bootstrap aws-down cost
tf-init: ## terraform init (needs TF_STATE_BUCKET)
	terraform -chdir=$(TF_AWS) init -backend-config="bucket=$(TF_STATE_BUCKET)"

tf-plan: ## terraform plan
	terraform -chdir=$(TF_AWS) plan

tf-apply: ## terraform apply (VPC, EKS, IAM, buckets) ~15 min
	terraform -chdir=$(TF_AWS) apply

eks-bootstrap: ## Install Argo CD on EKS and hand over to GitOps
	./scripts/eks-bootstrap.sh

aws-down: ## Delete load balancers first, then destroy all AWS resources
	-kubectl delete -n argocd -f deploy/argocd/root.yaml --wait=true
	-kubectl delete gateway --all -A --wait=true
	-kubectl delete svc -A --field-selector spec.type=LoadBalancer --wait=true
	terraform -chdir=$(TF_AWS) destroy

cost: ## What is LabOps costing this month?
	aws ce get-cost-and-usage --time-period Start=$$(date +%Y-%m-01),End=$$(date -d tomorrow +%F) \
	  --granularity MONTHLY --metrics UnblendedCost \
	  --filter '{"Tags":{"Key":"Project","Values":["labops"]}}' \
	  --query 'ResultsByTime[0].Total.UnblendedCost' --output table

##@ Game days
.PHONY: gameday-node gameday-bad-release gameday-rollback gameday-db
gameday-node: ## Game day 1: lose a node
	./chaos/gameday-1-node-failure.sh

gameday-bad-release: ## Game day 2: ship a faulty release (via Git)
	./chaos/gameday-2-bad-release.sh break

gameday-rollback: ## Game day 2: roll it back (git revert)
	./chaos/gameday-2-bad-release.sh rollback

gameday-db: ## Game day 3: kill the Postgres primary
	./chaos/gameday-3-db-failover.sh

##@ Linux (Ansible)
.PHONY: edge-up edge-harden edge-scan
edge-up: ## Start the local lab-edge VM (Vagrant)
	cd ansible && vagrant up

edge-harden: ## Harden + configure the lab-edge VM
	cd ansible && ansible-galaxy collection install -r requirements.yml && ansible-playbook playbooks/site.yml

edge-scan: ## CIS compliance scan (OpenSCAP) -> ansible/reports/
	cd ansible && ansible-playbook playbooks/compliance.yml

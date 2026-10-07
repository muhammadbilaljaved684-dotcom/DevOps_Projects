# Setup guide

Work through the stages in order. Each one is useful on its own, so you can stop after any of them and still have something to show.

## 0. Prerequisites

Docker, `kind`, `kubectl`, `helm` (v4), Python 3.12, `terraform` ≥ 1.10, AWS CLI v2, `jq`. For the Linux part: Vagrant + VirtualBox and `ansible-core`.

This copy is already configured for `github.com/muhammadbilaljaved684-dotcom/DevOps_Projects` (Argo CD repo URLs, the image name `ghcr.io/muhammadbilaljaved684-dotcom/labops`, the cosign signing identity Kyverno trusts, and the GitHub OIDC trust in Terraform). If you fork or rename the repo, update those references (`grep -rn muhammadbilaljaved684-dotcom .`).

## 1. App on your laptop (free, 10 minutes)

```bash
cd app && python -m venv .venv && . .venv/bin/activate && pip install -e '.[dev]' && pytest && cd ..
make dev && make demo     # http://localhost:8001
```

## 2. Kubernetes locally (free)

```bash
make kind-up              # app + CloudNativePG, same chart as prod
make kind-gitops          # Argo CD manages everything from your GitHub repo
```
For `kind-gitops` the repo must be pushed to GitHub and CI must have published a signed image, because Kyverno only admits signed images.

## 3. GitHub

1. Push the repo. Make the GHCR package **public** (Packages → labops → settings) so clusters can pull without credentials.
2. Settings → Environments → create `prod` with yourself as required reviewer.
3. Settings → Actions → General → allow GitHub Actions to create pull requests (used by `promote.yml`).
4. If you protect `main`, allow the `github-actions` bot to push (the dev deploy commit), or change `deploy-dev` in `ci.yml` to open a PR instead.
5. Install the Renovate GitHub App on the repo.

## 4. AWS (costs money; see docs/cost.md)

```bash
# one-time: state bucket
cd infra/terraform/bootstrap
terraform init && terraform apply -var state_bucket_name=labops-tfstate-$(aws sts get-caller-identity --query Account --output text)

# main stack
cd ../envs/aws && cp terraform.tfvars.example terraform.tfvars   # edit it
cd ../../../..
make tf-init TF_STATE_BUCKET=labops-tfstate-<account-id>
make tf-apply          # ~15 min
make eks-bootstrap     # Argo CD + GitOps hand-over, prints values to put in Git
```
Then set these **GitHub repository variables** from the Terraform outputs so CI can plan/apply: `AWS_PLAN_ROLE_ARN`, `AWS_APPLY_ROLE_ARN`, `TF_STATE_BUCKET`, `OWNER_EMAIL`, `EKS_VERSION`, `API_ALLOWED_CIDRS`, `ADMIN_PRINCIPAL_ARNS`.

Activate the `Project` cost allocation tag in the Billing console so the budget alarm filters correctly.

**When you're done:** `make aws-down`.

## 5. Microsoft Entra ID SSO (optional, needs an M365/Entra tenant)

See [entra-sso.md](entra-sso.md).

## 6. Linux edge server (free)

```bash
make edge-up          # Ubuntu 24.04 VM
make edge-scan        # CIS score BEFORE -> ansible/reports/
make edge-harden
make edge-scan        # CIS score AFTER
```
Put your SSH public key in `ansible/playbooks/group_vars/all.yml` first. Put both scores in the README.

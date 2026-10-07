# Entra ID side of the platform, kept in its own state because it lives in a
# different system (your Microsoft 365 tenant) with different credentials.
#   az login --tenant <your-tenant>      # an account that can create app registrations
#   terraform init -backend-config="bucket=labops-tfstate-<account-id>"
#   terraform apply
# Then run scripts/entra-secrets.sh to load the client secrets into the
# cluster as Kubernetes Secrets (never into Git).

terraform {
  required_version = ">= 1.10"
  required_providers {
    azuread = { source = "hashicorp/azuread", version = "~> 3.0" }
  }
  backend "s3" {
    key          = "envs/entra/terraform.tfstate"
    region       = "eu-central-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "azuread" {}

variable "argocd_host" {
  type    = string
  default = "argocd.labops.example.com"
}

variable "grafana_host" {
  type    = string
  default = "grafana.labops.example.com"
}

variable "restrict_to_groups" {
  type    = bool
  default = false
}

module "sso" {
  source             = "../../modules/entra-sso"
  name               = "labops"
  argocd_host        = var.argocd_host
  grafana_host       = var.grafana_host
  restrict_to_groups = var.restrict_to_groups
}

output "tenant_id" {
  value = module.sso.tenant_id
}

output "admins_group_id" {
  value = module.sso.admins_group_id
}

output "developers_group_id" {
  value = module.sso.developers_group_id
}

output "client_ids" {
  value = module.sso.client_ids
}

output "client_secrets" {
  value     = module.sso.client_secrets
  sensitive = true
}

# The whole AWS footprint: network, one EKS cluster (hosting the labops-dev
# and labops-prod namespaces), app buckets/roles, and GitHub OIDC roles.
# One cluster with two namespaces keeps the bill small; ADR 0003 explains
# when you would split into separate clusters/accounts instead.

terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = local.tags
  }
}

locals {
  name = "labops"
  tags = {
    Project   = "labops"
    ManagedBy = "terraform"
    Owner     = var.owner
    Repo      = "github.com/${var.github_owner}/${var.github_repo}"
  }
}

module "network" {
  source             = "../../modules/network"
  name               = local.name
  az_count           = var.az_count
  single_nat_gateway = var.single_nat_gateway
  flow_logs          = var.flow_logs
}

module "github_oidc" {
  source          = "../../modules/github-oidc"
  name            = local.name
  github_owner    = var.github_owner
  github_repo     = var.github_repo
  state_bucket    = var.state_bucket
  create_provider = var.create_github_oidc_provider
  tags            = local.tags
}

module "eks" {
  source             = "../../modules/eks"
  name               = local.name
  kubernetes_version = var.kubernetes_version
  vpc_id             = module.network.vpc_id
  private_subnet_ids = module.network.private_subnet_ids
  api_allowed_cidrs  = var.api_allowed_cidrs

  node_instance_types = var.node_instance_types
  node_capacity_type  = var.node_capacity_type
  node_min            = var.node_min
  node_max            = var.node_max
  node_desired        = var.node_desired

  # You (from the laptop) and the GitHub Actions apply role are cluster admins.
  admin_principal_arns = concat(var.admin_principal_arns, [module.github_oidc.apply_role_arn])
  tags = local.tags
}

module "app_iam" {
  source                = "../../modules/app-iam"
  name                  = "${local.name}-prod"
  oidc_provider_arn     = module.eks.oidc_provider_arn
  oidc_provider         = module.eks.oidc_provider
  app_namespace         = "labops-prod"
  force_destroy_buckets = var.force_destroy_buckets
  tags                  = local.tags
}

# Budget alarm: email when forecast spend passes the limit. The cheapest
# guard-rail there is. Activate "Project" as a cost allocation tag in the
# Billing console once, or the tag filter below matches nothing.
resource "aws_budgets_budget" "monthly" {
  name         = "${local.name}-monthly"
  budget_type  = "COST"
  limit_amount = var.monthly_budget_usd
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name   = "TagKeyValue"
    values = ["user:Project$labops"]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.budget_email]
  }
}

variable "region" {
  type    = string
  default = "eu-central-1"
}

variable "owner" {
  type        = string
  description = "Your name/email, used in tags"
}

variable "github_owner" {
  type        = string
  description = "GitHub user or org that owns the repo"
}

variable "github_repo" {
  type        = string
  description = "Repository name (CI's OIDC identity is trusted only for this repo)"
  default     = "DevOps_Projects"
}

variable "state_bucket" {
  type = string
}

variable "create_github_oidc_provider" {
  type    = bool
  default = true
}

variable "kubernetes_version" {
  type        = string
  description = "An EKS version in standard support; verify with `aws eks describe-cluster-versions --default-only`"
}

variable "admin_principal_arns" {
  type        = list(string)
  description = "Your IAM user/role ARN(s) for cluster-admin access (aws sts get-caller-identity)"
}

variable "api_allowed_cidrs" {
  type        = list(string)
  description = "Your public IP as x.x.x.x/32 (curl ifconfig.me)"
}

variable "az_count" {
  type    = number
  default = 2
}

variable "single_nat_gateway" {
  type    = bool
  default = true
}

variable "flow_logs" {
  type    = bool
  default = false
}

variable "node_instance_types" {
  type    = list(string)
  default = ["t3.large", "t3a.large"]
}

variable "node_capacity_type" {
  type    = string
  default = "SPOT"
}

variable "node_min" {
  type    = number
  default = 2
}

variable "node_max" {
  type    = number
  default = 4
}

variable "node_desired" {
  type    = number
  default = 3
}

variable "force_destroy_buckets" {
  type    = bool
  default = true
}

variable "monthly_budget_usd" {
  type    = string
  default = "60"
}

variable "budget_email" {
  type = string
}

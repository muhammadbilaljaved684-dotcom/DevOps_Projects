variable "name" {
  type = string
}

variable "kubernetes_version" {
  type        = string
  description = "Pick a version in EKS *standard* support (extended support costs ~6x more). Check: aws eks describe-cluster-versions"
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "api_allowed_cidrs" {
  type        = list(string)
  description = "CIDRs allowed to reach the public Kubernetes API (your home IP /32)."
  validation {
    condition     = !contains(var.api_allowed_cidrs, "0.0.0.0/0")
    error_message = "Do not expose the Kubernetes API to the whole internet."
  }
}

variable "admin_principal_arns" {
  type        = list(string)
  description = "IAM users/roles that get cluster-admin (e.g. your SSO admin role and the CI apply role)"
}

variable "extra_access_entries" {
  type        = any
  default     = {}
  description = "Additional EKS access entries (e.g. the GitHub Actions role)."
}

variable "node_instance_types" {
  type    = list(string)
  default = ["t3.large", "t3a.large"]
}

variable "node_capacity_type" {
  type    = string
  default = "SPOT"
  validation {
    condition     = contains(["SPOT", "ON_DEMAND"], var.node_capacity_type)
    error_message = "SPOT or ON_DEMAND."
  }
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
  default = 2
}

variable "tags" {
  type    = map(string)
  default = {}
}

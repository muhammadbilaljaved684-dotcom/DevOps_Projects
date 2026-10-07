variable "name" {
  type        = string
  description = "Prefix, e.g. labops-prod"
}

variable "oidc_provider_arn" {
  type = string
}

variable "oidc_provider" {
  type = string
}

variable "app_namespace" {
  type = string
}

variable "app_service_account" {
  type    = string
  default = "labops"
}

variable "pg_service_account" {
  type        = string
  default     = "labops-pg"
  description = "CloudNativePG creates a service account named after the Cluster"
}

variable "force_destroy_buckets" {
  type        = bool
  default     = false
  description = "true in dev so `terraform destroy` cleans up completely"
}

variable "tags" {
  type    = map(string)
  default = {}
}

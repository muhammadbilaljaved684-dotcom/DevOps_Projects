variable "name" {
  type = string
}

variable "github_owner" {
  type = string
}

variable "github_repo" {
  type    = string
  default = "DevOps_Projects"
}

variable "apply_environments" {
  type        = list(string)
  description = "GitHub Environments allowed to assume the apply role"
  default     = ["dev", "prod"]
}

variable "state_bucket" {
  type = string
}

variable "create_provider" {
  type        = bool
  default     = true
  description = "The GitHub OIDC provider is one per AWS account; set false in the second environment"
}

variable "tags" {
  type    = map(string)
  default = {}
}

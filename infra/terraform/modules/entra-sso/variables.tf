variable "name" {
  type    = string
  default = "labops"
}

variable "argocd_host" {
  type = string
}

variable "grafana_host" {
  type = string
}

variable "restrict_to_groups" {
  type        = bool
  default     = false
  description = "Require group assignment to sign in (needs Entra ID P1)"
}

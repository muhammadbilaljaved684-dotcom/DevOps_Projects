# Microsoft Entra ID (Azure AD) as the identity provider for the platform:
#   * two security groups: platform admins and developers
#   * app registrations for Argo CD and Grafana that emit group claims
# People get access by being added to an Entra group (joiner/mover/leaver is
# handled in Entra, not in each tool). This is the same identity model as
# Microsoft 365, so it doubles as an M365/Entra administration showcase.

terraform {
  required_providers {
    azuread = { source = "hashicorp/azuread", version = "~> 3.0" }
  }
}

data "azuread_client_config" "current" {}

resource "azuread_group" "admins" {
  display_name     = "${var.name}-platform-admins"
  description      = "Full admin in Argo CD and Grafana for ${var.name}"
  security_enabled = true
  owners           = [data.azuread_client_config.current.object_id]
}

resource "azuread_group" "developers" {
  display_name     = "${var.name}-developers"
  description      = "Can view everything and sync the dev environment"
  security_enabled = true
  owners           = [data.azuread_client_config.current.object_id]
}

locals {
  apps = {
    argocd = {
      display_name = "${var.name}-argocd"
      redirect_uri = "https://${var.argocd_host}/auth/callback"
    }
    grafana = {
      display_name = "${var.name}-grafana"
      redirect_uri = "https://${var.grafana_host}/login/azuread"
    }
  }
}

resource "azuread_application" "sso" {
  for_each         = local.apps
  display_name     = each.value.display_name
  owners           = [data.azuread_client_config.current.object_id]
  sign_in_audience = "AzureADMyOrg"

  # Put the user's security-group object IDs into the token.
  group_membership_claims = ["SecurityGroup"]

  web {
    redirect_uris = [each.value.redirect_uri]
    implicit_grant {
      id_token_issuance_enabled = false
    }
  }

  optional_claims {
    id_token {
      name = "groups"
    }
    access_token {
      name = "groups"
    }
  }

  required_resource_access {
    resource_app_id = "00000003-0000-0000-c000-000000000000" # Microsoft Graph
    resource_access {
      id   = "e1fe6dd8-ba31-4d61-89e7-88639da4683d" # User.Read (delegated)
      type = "Scope"
    }
  }
}

resource "azuread_service_principal" "sso" {
  for_each  = azuread_application.sso
  client_id = each.value.client_id
  owners    = [data.azuread_client_config.current.object_id]

  # Only members of the two groups may sign in at all. Assigning groups to
  # an enterprise app needs Entra ID P1 (included in M365 Business Premium /
  # E3+ trials); on the free tier leave restrict_to_groups = false and rely
  # on the group-to-role mapping in Argo CD / Grafana instead.
  app_role_assignment_required = var.restrict_to_groups
}

resource "azuread_app_role_assignment" "groups" {
  for_each = var.restrict_to_groups ? {
    for pair in setproduct(keys(local.apps), ["admins", "developers"]) :
    "${pair[0]}-${pair[1]}" => { app = pair[0], group = pair[1] }
  } : {}
  app_role_id         = "00000000-0000-0000-0000-000000000000" # default access
  principal_object_id = each.value.group == "admins" ? azuread_group.admins.object_id : azuread_group.developers.object_id
  resource_object_id  = azuread_service_principal.sso[each.value.app].object_id
}

resource "azuread_application_password" "sso" {
  for_each       = azuread_application.sso
  application_id = each.value.id
  display_name   = "terraform-managed"
  end_date       = timeadd(timestamp(), "4320h") # 180 days; rotate by re-applying

  lifecycle {
    ignore_changes = [end_date]
  }
}

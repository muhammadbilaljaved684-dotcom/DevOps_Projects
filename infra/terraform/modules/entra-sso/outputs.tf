output "tenant_id" {
  value = data.azuread_client_config.current.tenant_id
}

output "admins_group_id" {
  value = azuread_group.admins.object_id
}

output "developers_group_id" {
  value = azuread_group.developers.object_id
}

output "client_ids" {
  value = { for k, a in azuread_application.sso : k => a.client_id }
}

output "client_secrets" {
  value     = { for k, p in azuread_application_password.sso : k => p.value }
  sensitive = true
}

output "cluster_name" {
  value = module.eks.cluster_name
}

output "kubeconfig_command" {
  value = "aws eks update-kubeconfig --region ${var.region} --name ${module.eks.cluster_name}"
}

output "github_plan_role_arn" {
  description = "Set as GitHub variable AWS_PLAN_ROLE_ARN"
  value       = module.github_oidc.plan_role_arn
}

output "github_apply_role_arn" {
  description = "Set as GitHub variable AWS_APPLY_ROLE_ARN"
  value       = module.github_oidc.apply_role_arn
}

output "labops_irsa_role_arn" {
  description = "values-prod.yaml -> serviceAccount.annotations"
  value       = module.app_iam.app_role_arn
}

output "pg_role_arn" {
  description = "values-prod.yaml -> postgres.backup.roleArn"
  value       = module.app_iam.pg_role_arn
}

output "velero_role_arn" {
  value = module.app_iam.velero_role_arn
}

output "raw_bucket_name" {
  value = module.app_iam.raw_bucket_name
}

output "backup_bucket_name" {
  value = module.app_iam.backup_bucket_name
}

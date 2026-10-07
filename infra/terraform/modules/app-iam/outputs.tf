output "raw_bucket_name" {
  value = aws_s3_bucket.raw.bucket
}

output "backup_bucket_name" {
  value = aws_s3_bucket.backup.bucket
}

output "app_role_arn" {
  value = aws_iam_role.sa["app"].arn
}

output "pg_role_arn" {
  value = aws_iam_role.sa["pg"].arn
}

output "velero_role_arn" {
  value = aws_iam_role.sa["velero"].arn
}

# Remote state in the bootstrap bucket. Bucket name is passed at init time so
# it isn't hard-coded in Git:
#   terraform init -backend-config="bucket=labops-tfstate-<account-id>"
terraform {
  backend "s3" {
    key          = "envs/aws/terraform.tfstate"
    region       = "eu-central-1"
    encrypt      = true
    use_lockfile = true # S3-native locking (Terraform >= 1.10), no DynamoDB
  }
}

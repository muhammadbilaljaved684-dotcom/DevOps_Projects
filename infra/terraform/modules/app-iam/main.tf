# Everything the app needs from AWS, with least privilege and no static keys:
#   * raw-data bucket   -> app pods (IRSA role scoped to one service account)
#   * backup bucket     -> CloudNativePG WAL/base backups and Velero
# Each role trusts exactly one Kubernetes service account in one namespace.

terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
}

data "aws_caller_identity" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
}

# ---------- buckets ----------

resource "aws_s3_bucket" "raw" {
  bucket        = "${var.name}-raw-${local.account_id}"
  force_destroy = var.force_destroy_buckets
  tags          = var.tags
}

resource "aws_s3_bucket" "backup" {
  bucket        = "${var.name}-backup-${local.account_id}"
  force_destroy = var.force_destroy_buckets
  tags          = var.tags
}

resource "aws_s3_bucket_public_access_block" "all" {
  for_each                = { raw = aws_s3_bucket.raw.id, backup = aws_s3_bucket.backup.id }
  bucket                  = each.value
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "all" {
  for_each = { raw = aws_s3_bucket.raw.id, backup = aws_s3_bucket.backup.id }
  bucket   = each.value
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "backup" {
  bucket = aws_s3_bucket.backup.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Raw spectra are cheap to keep but rarely read: move to Infrequent Access
# after 30 days, expire after a year. Backups expire after 35 days.
resource "aws_s3_bucket_lifecycle_configuration" "raw" {
  bucket = aws_s3_bucket.raw.id
  rule {
    id     = "tiering"
    status = "Enabled"
    filter {}
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    expiration {
      days = 365
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "backup" {
  bucket = aws_s3_bucket.backup.id
  rule {
    id     = "expire-old-backups"
    status = "Enabled"
    filter {}
    expiration {
      days = 35
    }
    noncurrent_version_expiration {
      noncurrent_days = 7
    }
  }
}

# ---------- IRSA roles ----------

locals {
  service_accounts = {
    app    = { namespace = var.app_namespace, name = var.app_service_account }
    pg     = { namespace = var.app_namespace, name = var.pg_service_account }
    velero = { namespace = "velero", name = "velero-server" }
  }
}

data "aws_iam_policy_document" "trust" {
  for_each = local.service_accounts
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [var.oidc_provider_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${var.oidc_provider}:sub"
      values   = ["system:serviceaccount:${each.value.namespace}:${each.value.name}"]
    }
    condition {
      test     = "StringEquals"
      variable = "${var.oidc_provider}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "sa" {
  for_each           = local.service_accounts
  name               = "${var.name}-${each.key}"
  assume_role_policy = data.aws_iam_policy_document.trust[each.key].json
  tags               = var.tags
}

data "aws_iam_policy_document" "app" {
  statement {
    sid       = "RawObjects"
    actions   = ["s3:PutObject", "s3:GetObject"]
    resources = ["${aws_s3_bucket.raw.arn}/raw/*"]
  }
}

data "aws_iam_policy_document" "pg" {
  statement {
    actions   = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.backup.arn}/cnpg/*"]
  }
  statement {
    actions   = ["s3:ListBucket", "s3:GetBucketLocation"]
    resources = [aws_s3_bucket.backup.arn]
  }
}

data "aws_iam_policy_document" "velero" {
  statement {
    actions   = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject", "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts"]
    resources = ["${aws_s3_bucket.backup.arn}/velero/*"]
  }
  statement {
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.backup.arn]
  }
  statement {
    actions = [
      "ec2:DescribeVolumes", "ec2:DescribeSnapshots", "ec2:CreateTags",
      "ec2:CreateVolume", "ec2:CreateSnapshot", "ec2:DeleteSnapshot",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "sa" {
  for_each = {
    app    = data.aws_iam_policy_document.app.json
    pg     = data.aws_iam_policy_document.pg.json
    velero = data.aws_iam_policy_document.velero.json
  }
  name   = "${var.name}-${each.key}"
  role   = aws_iam_role.sa[each.key].id
  policy = each.value
}

# EKS control plane + one managed node group on AL2023.
# Uses terraform-aws-modules/eks v21 input names (name, kubernetes_version,
# addons, endpoint_public_access). If you pin v20 instead, these were
# cluster_name, cluster_version, cluster_addons, cluster_endpoint_public_access.

terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 21.0"

  name               = var.name
  kubernetes_version = var.kubernetes_version

  vpc_id     = var.vpc_id
  subnet_ids = var.private_subnet_ids

  # Public API endpoint limited to your IP(s); nodes talk to it privately.
  endpoint_public_access       = true
  endpoint_public_access_cidrs = var.api_allowed_cidrs
  endpoint_private_access      = true

  # EKS access entries instead of the old aws-auth ConfigMap. Admins are
  # listed explicitly rather than "whoever ran terraform apply", otherwise the
  # entry flips between your laptop and CI and someone gets locked out.
  enable_cluster_creator_admin_permissions = false
  access_entries = merge(
    {
      for i, arn in var.admin_principal_arns : "admin-${i}" => {
        principal_arn = arn
        policy_associations = {
          admin = {
            policy_arn   = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
            access_scope = { type = "cluster" }
          }
        }
      }
    },
    var.extra_access_entries,
  )

  # Secrets encrypted with a dedicated KMS key; control-plane audit logs on.
  enabled_log_types = ["api", "audit", "authenticator"]

  addons = {
    coredns    = {}
    kube-proxy = {}
    vpc-cni = {
      before_compute = true
      # Enables NetworkPolicy enforcement with the VPC CNI, so the
      # NetworkPolicies in the Helm chart are actually applied.
      configuration_values = jsonencode({ enableNetworkPolicy = "true" })
    }
    eks-pod-identity-agent = { before_compute = true }
    aws-ebs-csi-driver = {
      service_account_role_arn = aws_iam_role.ebs_csi.arn
    }
  }

  eks_managed_node_groups = {
    default = {
      ami_type       = "AL2023_x86_64_STANDARD"
      instance_types = var.node_instance_types
      capacity_type  = var.node_capacity_type # SPOT in dev = ~70% cheaper
      min_size       = var.node_min
      max_size       = var.node_max
      desired_size   = var.node_desired

      # IMDSv2 only, hop limit 1: pods can't steal the node's IAM role.
      metadata_options = {
        http_endpoint               = "enabled"
        http_tokens                 = "required"
        http_put_response_hop_limit = 1
      }

      labels = { workload = "general" }
    }
  }

  tags = var.tags
}

# IAM role for the EBS CSI driver (gp3 volumes for Postgres).
data "aws_iam_policy_document" "ebs_csi_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [module.eks.oidc_provider_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${module.eks.oidc_provider}:sub"
      values   = ["system:serviceaccount:kube-system:ebs-csi-controller-sa"]
    }
    condition {
      test     = "StringEquals"
      variable = "${module.eks.oidc_provider}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ebs_csi" {
  name               = "${var.name}-ebs-csi"
  assume_role_policy = data.aws_iam_policy_document.ebs_csi_trust.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "ebs_csi" {
  role       = aws_iam_role.ebs_csi.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
}

# Default gp3 StorageClass is created by the Makefile bootstrap
# (deploy/platform/storageclass-gp3.yaml) to keep Terraform free of the
# kubernetes provider, which avoids the classic "cluster not yet ready" race.

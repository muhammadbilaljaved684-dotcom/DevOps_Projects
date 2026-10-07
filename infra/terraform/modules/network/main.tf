# VPC with public subnets (load balancers, NAT) and private subnets (nodes).
# Nodes never get public IPs. Subnet tags let the AWS Load Balancer
# Controller / Envoy Gateway service find the right subnets.

terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, var.az_count)
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 6.0"

  name = var.name
  cidr = var.cidr
  azs  = local.azs

  private_subnets = [for i, _ in local.azs : cidrsubnet(var.cidr, 4, i)]
  public_subnets  = [for i, _ in local.azs : cidrsubnet(var.cidr, 8, 48 + i)]

  enable_nat_gateway     = true
  single_nat_gateway     = var.single_nat_gateway # one NAT in dev saves ~$35/month per AZ
  one_nat_gateway_per_az = !var.single_nat_gateway
  enable_dns_hostnames   = true

  # VPC flow logs to CloudWatch for incident investigation.
  enable_flow_log                                 = var.flow_logs
  create_flow_log_cloudwatch_log_group            = var.flow_logs
  create_flow_log_cloudwatch_iam_role             = var.flow_logs
  flow_log_cloudwatch_log_group_retention_in_days = 14

  public_subnet_tags  = { "kubernetes.io/role/elb" = 1 }
  private_subnet_tags = { "kubernetes.io/role/internal-elb" = 1 }
}

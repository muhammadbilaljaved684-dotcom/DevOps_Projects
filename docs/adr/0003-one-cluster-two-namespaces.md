# ADR 0003: One EKS cluster with dev and prod namespaces

**Status:** accepted for this project; would be rejected in a company

## Context
Separate clusters (or AWS accounts) per environment are best practice: blast-radius isolation, independent upgrades, separate IAM. They also double the fixed cost (~$2.40/day per control plane plus NAT and nodes).

## Decision
One cluster, `labops-dev` and `labops-prod` namespaces, isolated with: separate Argo CD Applications and AppProject destinations, NetworkPolicies, Kyverno policies, separate IRSA roles (prod only has S3 access), and different sync policies.

## Consequences
- Half the cost, which matters for a personal account.
- A cluster upgrade hits both environments at once; a noisy dev workload can starve prod (mitigated by requests/limits; a ResourceQuota on dev would be the next step).
- **What I'd do in a company:** AWS Organizations with separate dev/prod accounts, one cluster per account, Argo CD in a management cluster deploying to both.

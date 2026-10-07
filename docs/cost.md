# Cost

Rough on-demand prices for eu-central-1; check the AWS pricing pages for current numbers before you rely on them.

| Item | Approx. per day | Notes |
|---|---|---|
| EKS control plane | ~$2.40 | $0.10/h. Only in **standard** support; extended support is ~6× more, so keep the version current |
| NAT gateway (1) | ~$1.10 + data | `single_nat_gateway = true` in the demo profile |
| 3 × t3.large **spot** nodes | ~$2–3 | Spot is roughly 60–70% cheaper than on-demand |
| Network load balancer (Gateway) | ~$0.55 | Created by Envoy Gateway |
| EBS gp3 (Postgres, ~20 GB) | ~$0.10 | |
| S3, CloudWatch, KMS | cents | |
| **Total while running** | **≈ $6–8 / day** | |

## How to keep it cheap

- Do all development on `kind` (free). Use EKS only for a weekend: deploy, run the game days, record the video and screenshots, then `make aws-down`.
- The budget alarm emails you at 80% of the forecast monthly budget (`monthly_budget_usd`).
- `make cost` shows month-to-date spend for resources tagged `Project=labops`.
- `make aws-down` deletes load balancers *before* `terraform destroy`; otherwise the VPC can't be deleted because Kubernetes-created ELBs still hold its subnets.

## Interview angle

"What does your platform cost?" is a common question. Have the number ready, and explain which single change saved the most (spot nodes) and what you'd change for production (on-demand for the system node group, NAT per AZ, separate accounts).

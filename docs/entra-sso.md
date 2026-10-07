# Microsoft Entra ID single sign-on

Argo CD and Grafana log in through Microsoft Entra ID (the identity system behind Microsoft 365). Access is granted by **Entra group membership**: add someone to `labops-developers` and they can view everything and sync dev; add them to `labops-platform-admins` and they're admin. Remove them from the group and access is gone everywhere. That is the joiner/mover/leaver process an IT team actually runs.

## What Terraform creates (`infra/terraform/envs/entra`)

- Security groups `labops-platform-admins` and `labops-developers`
- App registrations `labops-argocd` and `labops-grafana`, configured to put group IDs in the token (`groupMembershipClaims = SecurityGroup`)
- Client secrets with a 180-day lifetime (rotation = re-apply)
- Optionally (`restrict_to_groups = true`, needs Entra ID P1): users not in either group can't sign in at all

## Steps

```bash
az login --tenant <your-tenant-id>      # account allowed to create app registrations
cd infra/terraform/envs/entra
terraform init -backend-config="bucket=labops-tfstate-<account-id>"
terraform apply -var argocd_host=argocd.<your-domain> -var grafana_host=grafana.<your-domain>
cd ../../../..
./scripts/entra-secrets.sh               # secrets -> Kubernetes, prints IDs for values-entra.yaml
# edit deploy/argocd/install/values-entra.yaml with the printed IDs, then:
ENTRA=1 ./scripts/eks-bootstrap.sh
```

Add yourself to `labops-platform-admins` in the Entra admin center, sign out of Argo CD, and sign in with Microsoft.

## Getting a tenant

Any Microsoft 365 business tenant works (including a trial). Check whether you qualify for the Microsoft 365 Developer Program sandbox; eligibility has been restricted in recent years. Group-restricted sign-in needs Entra ID P1, which is included in Microsoft 365 Business Premium and E3/E5 trials.

## Things to be ready to explain

- Why groups, not individual users, in the role mappings.
- Why the token carries group **object IDs** rather than names (names can be changed by anyone with rights on the group; IDs can't be spoofed).
- What happens for users in more than 200 groups (Entra sends an "overage" claim instead of the list; the app must then call Microsoft Graph).

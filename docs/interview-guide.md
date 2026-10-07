# Interview guide

How to present this project, and the questions it invites. Practise answering these out loud; the project only helps if you can explain every decision in it.

## The 60-second pitch

"During my MSc I measured NV-centre spectra by hand. LabOps is the platform I'd want for that: a hardened Linux edge server ships instrument files to a Kubernetes service on AWS that fits them and serves results. Everything is code: Terraform for AWS, Ansible for the Linux server, Argo CD deploying from Git. Images are scanned, signed by CI and verified by Kyverno before they can run. I defined an SLO, 99% of uploads processed within 30 seconds, with burn-rate alerts, and I broke the system on purpose four times to prove the recovery works. My favourite: I shipped a bad release, the alert fired in about four minutes, and a `git revert` fixed it."

Then stop and let them pick what to ask about.

## Questions you should expect

**GitOps / CD**
- Why doesn't CI deploy directly? *(ADR 0001: no cluster credentials outside the cluster, drift correction, audit trail, rollback = revert.)*
- What happens if someone runs `kubectl edit` in prod? *(Self-heal reverts it; show game day 2.)*
- How do you promote to prod? *(Workflow opens a PR; merge inside the sync window.)*

**Security**
- How do pods get AWS access without keys? *(IRSA: projected service-account token → STS AssumeRoleWithWebIdentity → role trusted only for that namespace/service account.)*
- What stops an attacker pushing a malicious image? *(Keyless signature bound to the CI workflow identity; Kyverno verifies it at admission and pins the digest.)*
- Why Pod Security Admission *and* Kyverno? *(PSA is built into the API server and covers the restricted profile with zero moving parts; Kyverno handles what PSA can't express: signatures, tags, resource limits. Kyverno's old `ClusterPolicy` is deprecated, so the policies use the CEL-based `ValidatingPolicy`/`ImageValidatingPolicy`.)*
- Why pin GitHub Actions to SHAs? *(Tags are mutable; there have been real incidents of popular actions' tags being repointed to malicious code.)*
- How does CI reach AWS? *(OIDC; plan role read-only from PRs, apply role only from an approved Environment.)*

**Kubernetes**
- Liveness vs readiness: why doesn't liveness check Redis? *(A dependency outage would restart every pod and make things worse; readiness takes the pod out of rotation instead.)*
- How do you survive a node loss? *(Replicas ≥ 2, topology spread across nodes/zones, PDBs, `maxUnavailable: 0`.)*
- Why does the worker scale on CPU and not queue depth? *(Simplicity; KEDA scaling on Redis list length would be better. Know this trade-off.)*

**Observability**
- Explain your SLO and error budget. *(99% over 30 days → 1% budget, about 7.2 hours of "bad" per month at constant traffic.)*
- Why multi-window burn-rate alerts? *(Fast detection of big problems, no paging for blips, alerts reset quickly after recovery.)*
- What does a 14.4× burn rate mean? *(At that rate the 30-day budget lasts about 2 days; 1 hour of it uses 2% of the budget.)*

**Terraform**
- How is state stored and locked? *(S3 with versioning and KMS, S3-native lock files; no DynamoDB needed since Terraform 1.10.)*
- Why are EKS admins listed explicitly instead of "cluster creator"? *(Otherwise the creator entry flips between laptop and CI and someone gets locked out.)*
- What happens on `terraform destroy` with Kubernetes load balancers still around? *(VPC deletion fails; `make aws-down` deletes them first.)*

**Linux**
- What does your hardening actually change? *(Show OpenSCAP before/after scores; name 3 rules: SSH root login off, auditd watching identity files, nftables default-deny.)*
- How do you patch without downtime? *(Rolling play, `serial: 1`, reboot only if required, health check after each host, stop on first failure.)*
- How does the uploader avoid a retry storm? *(systemd path unit on close-write, plus a 5-minute retry timer; 4xx files set aside, not retried.)*

**Identity**
- How do people get access? *(Entra security groups mapped to roles in Argo CD/Grafana; leaver removed from the group loses access everywhere.)*

## Questions to ask them back

- "How do you deploy to production today, and how do you roll back?"
- "Do you have SLOs, or do you alert on resource metrics?"
- "How do you handle access when someone leaves the team?"

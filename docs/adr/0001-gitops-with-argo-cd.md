# ADR 0001: Deploy with GitOps (Argo CD), not from CI

**Status:** accepted

## Context
CI could run `helm upgrade` against the cluster at the end of the pipeline. That needs cluster credentials in CI, the cluster's real state can drift from Git (someone runs `kubectl edit`), and rollback means re-running an old pipeline.

## Decision
CI only builds, signs and writes the new image tag into Git. Argo CD, running inside the cluster, pulls from Git and applies. Dev auto-syncs; prod syncs from `main` only, with self-heal on, prune manual, and a sync window.

## Consequences
- No cluster credentials outside the cluster.
- Git is the audit log: who deployed what, when, approved by whom.
- Rollback is `git revert`, and it's the same process as a deploy.
- Manual hot-fixes are reverted by self-heal, which is intended (game day 2 shows it), but on-call must know to fix through Git.
- One more component to run and upgrade (Argo CD itself).

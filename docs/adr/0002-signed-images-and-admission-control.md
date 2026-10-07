# ADR 0002: Only run images signed by our own CI (cosign + Kyverno)

**Status:** accepted

## Context
Scanning images in CI doesn't stop someone pushing an unscanned image to the registry and pointing a Deployment at it. Supply-chain attacks (compromised dependencies, hijacked CI actions) make "where did this image come from?" a real question.

## Decision
- CI signs each image **keyless** with cosign: the signature is bound to the identity `…/.github/workflows/ci.yml@refs/heads/main` through GitHub OIDC and recorded in the public Rekor transparency log. There is no signing key to steal or rotate.
- CI also attaches an SPDX SBOM as a signed attestation.
- Kyverno verifies both at admission time with an `ImageValidatingPolicy` (`policies.kyverno.io/v1`, CEL-based) and rewrites the image reference to the verified digest. The older `ClusterPolicy` type is deprecated in current Kyverno releases (1.19 warns on it), so new policies use the CEL types.
- The "restricted" Pod Security Standard is enforced by Kubernetes' built-in Pod Security Admission (namespace labels set via Argo CD `managedNamespaceMetadata`), not by Kyverno. Kyverno `ValidatingPolicy` covers only what PSA doesn't: no `:latest`/untagged images, and resource requests/limits.
- All GitHub Actions are pinned to commit SHAs; Renovate proposes updates.

## Consequences
- An image built anywhere else (a laptop, a fork, a PR branch) cannot run in labops namespaces.
- Admission depends on reaching Sigstore; if it's unreachable, new pods are rejected (fail closed). For a lab this is acceptable; a regulated company might run its own Sigstore stack or use key-based signing with KMS.
- Local `kind-up` uses an unsigned local image, which is allowed because the policy only matches the GHCR repository.

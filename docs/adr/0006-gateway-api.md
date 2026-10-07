# ADR 0006: Gateway API (Envoy Gateway) instead of Ingress-NGINX

**Status:** accepted

## Context
The Kubernetes Ingress-NGINX controller has been retired by its maintainers, so new platforms shouldn't adopt it. The Gateway API is the successor to the Ingress resource, with a role split between platform teams (Gateway) and app teams (HTTPRoute).

## Decision
The platform layer runs Envoy Gateway and one shared `Gateway`. The LabOps chart only ships an `HTTPRoute` that attaches to it, routing `POST /api/v1/uploads` to ingest-api and everything else to results-api. The Gateway only accepts routes from the two LabOps namespaces.

## Consequences
- App teams can't change listeners, ports or TLS; the platform team can't accidentally break app routing.
- Method-based routing (POST only to ingest) needs no annotations.
- Envoy Gateway is another component to upgrade (Renovate tracks it).

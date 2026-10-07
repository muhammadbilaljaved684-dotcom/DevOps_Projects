#!/usr/bin/env bash
# GAME DAY 1 - lose a node.
# Hypothesis: with 2+ replicas spread across nodes and PodDisruptionBudgets,
# losing one node causes no failed uploads and the SLO is unaffected.
#
#   ./chaos/gameday-1-node-failure.sh            # kind: stops a worker container
#   ./chaos/gameday-1-node-failure.sh --eks      # EKS: terminates an EC2 node
#
# Run `make load` in another terminal first so there is traffic to observe.
set -euo pipefail
NS="${NS:-labops-dev}"

echo "== Before"
kubectl -n "$NS" get pods -o wide
NODE=$(kubectl -n "$NS" get pod -l app.kubernetes.io/component=worker \
        -o jsonpath='{.items[0].spec.nodeName}')
echo "== Target node: $NODE  (start: $(date -u +%T))"

if [[ "${1:-}" == "--eks" ]]; then
  ID=$(kubectl get node "$NODE" -o jsonpath='{.spec.providerID}' | awk -F/ '{print $NF}')
  aws ec2 terminate-instances --instance-ids "$ID" >/dev/null
  echo "Terminated $ID. The managed node group will replace it."
else
  docker stop "$NODE" >/dev/null
  echo "Stopped kind node container $NODE. Restore later with: docker start $NODE"
fi

echo "== Watching recovery for 3 minutes (Ctrl-C to stop)"
end=$((SECONDS + 180))
while (( SECONDS < end )); do
  ready=$(kubectl -n "$NS" get deploy -o jsonpath='{range .items[*]}{.metadata.name}={.status.readyReplicas}/{.spec.replicas} {end}')
  echo "$(date -u +%T)  $ready"
  sleep 10
done

cat <<EOF

Now record in docs/game-days/ (template: docs/postmortems/TEMPLATE.md):
  * time until pods were rescheduled (from the log above)
  * failed uploads during the window (Grafana: "Jobs per second by outcome")
  * did any alert fire? should it have?
EOF

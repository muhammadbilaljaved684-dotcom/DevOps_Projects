#!/usr/bin/env bash
# GAME DAY 2 - ship a bad release and roll it back the GitOps way.
# Hypothesis: a release that fails ~50% of jobs triggers the fast-burn SLO
# alert within ~5 minutes, and `git revert` restores service with no kubectl.
#
# The "bad release" is the worker's built-in fault switch (error-half),
# so you can rehearse this safely as many times as you like.
#
#   ./chaos/gameday-2-bad-release.sh break     # commit the bad config
#   ./chaos/gameday-2-bad-release.sh rollback  # revert it
#   LOCAL=1 ./chaos/gameday-2-bad-release.sh break   # kind without Argo CD (helm)
set -euo pipefail
cd "$(dirname "$0")/.."
VALUES=deploy/helm/labops/values-dev.yaml
ACTION="${1:?usage: break|rollback}"

if [[ "${LOCAL:-0}" == "1" ]]; then
  MODE=$([[ "$ACTION" == "break" ]] && echo error-half || echo "")
  helm upgrade labops deploy/helm/labops -n labops-dev --reuse-values \
    --set-string config.faultMode="$MODE" --wait
  echo "fault mode now: '${MODE:-off}'"
  exit 0
fi

case "$ACTION" in
  break)
    # Add (or replace) faultMode under the existing config: block.
    if grep -q '^  faultMode:' "$VALUES"; then
      sed -i -E 's/^  faultMode:.*/  faultMode: error-half/' "$VALUES"
    else
      sed -i -E 's/^config:$/config:\n  faultMode: error-half/' "$VALUES"
    fi
    git add "$VALUES"
    git commit -m "chore(dev): game day 2 - deploy faulty worker config"
    git push
    echo "Pushed at $(date -u +%T). Watch: Argo CD sync -> Grafana SLI -> Alertmanager."
    echo "Try 'kubectl edit' to fix it by hand and watch Argo CD self-heal undo you."
    ;;
  rollback)
    SHA=$(git log --grep='game day 2 - deploy faulty' -n1 --format=%H)
    [[ -n "$SHA" ]] || { echo "no game-day commit found"; exit 1; }
    git revert --no-edit "$SHA"
    git push
    echo "Reverted at $(date -u +%T). Measure: time from alert to recovery = your MTTR."
    ;;
  *) echo "usage: break|rollback"; exit 1 ;;
esac

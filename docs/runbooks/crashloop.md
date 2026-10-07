# Runbook: LabOpsPodCrashLooping

```bash
NS=labops-prod
POD=$(kubectl -n $NS get pods --field-selector=status.phase!=Succeeded -o json \
      | jq -r '.items[] | select(.status.containerStatuses[]?.restartCount > 3) | .metadata.name' | head -1)
kubectl -n $NS logs "$POD" --previous | tail -50
kubectl -n $NS describe pod "$POD" | grep -A5 "Last State"
```

| Signal | Cause | Fix |
|---|---|---|
| `OOMKilled` | Memory limit too low (large spectra?) | Raise `resources.limits.memory` for that component via PR |
| `Read-only file system` | Code writing outside `/tmp` | Fix the code; the read-only root filesystem is intentional |
| Database connection refused at startup | Postgres failing over or down | Check the CNPG cluster; pods recover on their own when it's back |
| Liveness probe failed | Event loop blocked, or probe too aggressive | Check probe timings in the chart; liveness must never depend on Redis/DB |

If the crash started right after a deploy: roll back first (`git revert`), investigate second.

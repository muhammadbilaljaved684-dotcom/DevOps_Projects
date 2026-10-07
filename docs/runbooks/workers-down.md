# Runbook: LabOpsWorkersDown

**Meaning:** Prometheus can't scrape any worker for 3 minutes. Uploads are accepted but nothing is processed.

```bash
NS=labops-prod
kubectl -n $NS get pods -l app.kubernetes.io/component=worker -o wide
kubectl -n $NS describe pod -l app.kubernetes.io/component=worker | tail -30
kubectl -n $NS get events --sort-by=.lastTimestamp | tail -20
```

| Pod state | Likely cause | Fix |
|---|---|---|
| `Pending` | No node capacity / spot nodes reclaimed | `kubectl get nodes`; the node group replaces spot nodes in a few minutes. If not, check the ASG in EC2 |
| `ImagePullBackOff` | Tag doesn't exist, or GHCR package private | Check the tag in values; make the package public |
| Rejected by admission (events mention Kyverno) | Image not signed by CI on main | Never bypass the policy: rebuild through CI |
| `CrashLoopBackOff` | See [crashloop](crashloop.md) | |
| Running but not scraped | NetworkPolicy blocks Prometheus, or ServiceMonitor label mismatch | `kubectl -n monitoring port-forward svc/kube-prometheus-stack-prometheus 9090` → Status → Targets |

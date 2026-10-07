# Game days

A game day is a planned failure with a written hypothesis. Run each one with steady load (`make load`) and Grafana open, then write the result up with the [postmortem template](../postmortems/TEMPLATE.md) and save it in this folder as `YYYY-MM-DD-<name>.md`.

| # | Script | Hypothesis | Measure |
|---|---|---|---|
| 1 | `make gameday-node` | Losing one node causes no failed uploads | Reschedule time, failed jobs, did any alert fire |
| 2 | `make gameday-bad-release` then `make gameday-rollback` | Fast-burn alert fires within 5 min; `git revert` restores service; `kubectl edit` fixes get undone by Argo CD self-heal | Time to detect, time to mitigate |
| 3 | `make gameday-db` | Postgres failover < 30 s, no data loss | Failover time, errors during switch |
| 4 | `chaos/gameday-4-restore-drill.sh` (EKS) | Namespace restorable from backup | RTO in minutes |

## Tips

- **Write the hypothesis before you start.** A game day where the hypothesis turns out wrong is the most valuable kind, and the best interview story.
- Record your screen for game day 2. Ninety seconds showing the alert, the revert, and the graph recovering is the strongest thing on your profile.
- Put the measured numbers in the README results table.

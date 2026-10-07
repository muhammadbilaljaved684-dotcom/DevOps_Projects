# ADR 0005: Page on SLO burn rate, not on CPU or pod restarts

**Status:** accepted

## Context
Alerting on causes (CPU > 80%, pod restarted) produces noise that doesn't correlate with user pain, and misses failures that don't show up as resource usage (e.g. a bug that fails half the jobs at low CPU).

## Decision
- SLI: share of uploads that **succeed and have a result within 30 s**.
- SLO: 99% over 30 days → 1% error budget.
- Paging alerts use multi-window, multi-burn-rate rules from the Google SRE Workbook: 14.4× over 1 h confirmed by 5 m, and 6× over 6 h confirmed by 30 m. A slow 3-day leak opens a ticket instead of paging.
- Cause-based signals (queue backlog, crash loops) are **tickets**, not pages, and each alert links to a runbook.

## Consequences
- Pages mean users are affected, and the short confirmation window means they stop quickly after recovery.
- The SLO only covers jobs that finish; a job that never finishes isn't counted. That's why queue backlog and "workers down" exist as separate alerts.
- Thresholds are tuned for real traffic. With very low traffic a single failure is a large percentage; for the demo, generate steady load with `make load`.

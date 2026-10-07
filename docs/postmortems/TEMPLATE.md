# Postmortem: <short title>

**Date:** YYYY-MM-DD · **Duration:** HH:MM–HH:MM UTC (X min) · **Severity:** page / ticket
**Author:** · **Status:** draft / reviewed
**Blameless:** this document describes what the system and process allowed to happen, not who to blame.

## Summary
Two or three sentences: what broke, who was affected, how it was fixed.

## Impact
- Uploads affected: N (X% of traffic in the window)
- Error budget consumed: X% of the monthly budget
- Data lost: none / describe

## Timeline (UTC)
| Time | Event |
|---|---|
| 10:00 | Change merged (link to commit/PR) |
| 10:02 | Argo CD synced |
| 10:06 | `LabOpsSLOFastBurn` fired |
| 10:09 | On-call acknowledged, opened dashboard |
| 10:12 | Cause identified |
| 10:13 | `git revert` pushed |
| 10:15 | Error rate back to normal |

**Time to detect:** X min · **Time to mitigate:** Y min

## Root cause
What actually caused it. Ask "why" until you reach something the process could have caught.

## What went well
-

## What went badly
-

## Where we got lucky
-

## Action items
| Action | Type (prevent / detect / mitigate) | Owner | Issue |
|---|---|---|---|
| | | | |

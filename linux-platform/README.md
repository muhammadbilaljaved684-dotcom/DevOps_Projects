# Acme Analytics: a hardened, observable and recoverable Linux platform

> **Status: in progress.** Built step by step in VMware. Each working day is documented in [`docs/progress/`](docs/progress/).

![Project 2 architecture](docs/project2-architecture.png)

## The problem

Acme Analytics runs a small web app on one server. Disks fill up without warning, backups depend on someone remembering, logs grow forever, admins SSH in from anywhere, nobody notices an outage until a customer emails, and nobody could rebuild the server the same way. The first enterprise customer's security questionnaire asks questions the team cannot answer.

My job as junior platform engineer: build a platform that is **recoverable, observable and least-privilege**, run it like a service desk, and document it.

## What I am building

| VM | Role | IP |
|---|---|---|
| gw01 | Gateway: NAT, iptables firewall, WireGuard VPN, Ansible control node | 192.168.60.1 |
| app01 | App server: nginx in Docker, monitoring stack (Prometheus, Alertmanager, Grafana) | 192.168.60.10 |
| stor01 | Storage: LVM, NFS, backups, central log server | 192.168.60.20 |
| svc01 | Service desk: GLPI tickets, knowledge base, asset inventory | 192.168.60.40 |

## Progress

| Phase | Topic | Status | Report |
|---|---|---|---|
| 0 | Know the system: kernel, boot, targets | 🟡 gw01 done | [Day 1](docs/progress/day-01-2026-10-13.md) |
| 1 | Network foundation: static IPs, routing, NAT | ⏳ | |
| 1A | Service desk: GLPI tickets and inventory | ⏳ | |
| 2 | Storage: LVM, NFS, backups, snapshots | ⏳ | |
| 3 | Automation: systemd services and timers | ⏳ | |
| 4 | Processes, signals, cgroups | ⏳ | |
| 5 | Logging: journald, rsyslog, logrotate | ⏳ | |
| 5A | Monitoring and alerting | ⏳ | |
| 6 | Security hardening | ⏳ | |
| 6A | WireGuard VPN | ⏳ | |
| 7 | Publish the web service (DNAT) | ⏳ | |
| 7A | Ansible: rebuild and joiner/leaver | ⏳ | |
| 8 | Acceptance tests and disaster drill | ⏳ | |

## Repository layout

```text
linux-platform/
  README.md                     this page
  docs/
    project2-architecture.png   architecture diagram
    progress/                   one technical report per working day
  evidence/                     raw command output per day (added as the project grows)
```

## Results

*Filled in with measured numbers after Phase 8: time to detect each alert, rebuild time, RTO/RPO, tickets handled.*

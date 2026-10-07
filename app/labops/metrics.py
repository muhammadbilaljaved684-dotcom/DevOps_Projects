"""Prometheus metrics shared by all roles.

The SLO rules in deploy/helm/labops/templates/prometheusrule.yaml are built
on labops_job_e2e_seconds, so the bucket boundaries include the 30 s target.
"""

from prometheus_client import Counter, Gauge, Histogram

UPLOADS = Counter("labops_uploads_total", "Spectrum uploads accepted or rejected", ["outcome"])

JOBS = Counter("labops_jobs_total", "Jobs finished by the worker", ["outcome"])

JOB_E2E = Histogram(
    "labops_job_e2e_seconds",
    "Time from upload to result available (the SLI); outcome=success|failed|error",
    ["outcome"],
    buckets=(0.5, 1, 2, 5, 10, 20, 30, 45, 60, 120, 300),
)

JOB_PROCESSING = Histogram(
    "labops_job_processing_seconds",
    "Time the worker spends fitting one spectrum",
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30),
)

QUEUE_DEPTH = Gauge("labops_queue_depth", "Jobs waiting in the queue")

FAULT_MODE = Gauge("labops_fault_mode_enabled", "1 if fault injection is active", ["mode"])

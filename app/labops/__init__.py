"""LabOps: measurement-data processing platform.

One codebase, three runtime roles (selected by the container command):
  * ingest-api  - accepts spectrum uploads, stores raw data, enqueues a job
  * worker      - fits resonance dips and writes results
  * results-api - serves results and a small dashboard
"""

__version__ = "0.1.0"

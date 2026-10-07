# syntax=docker/dockerfile:1.7
#
# One image, three roles. The Kubernetes Deployment chooses the role:
#   ingest-api : uvicorn labops.ingest_api:app
#   results-api: uvicorn labops.results_api:app
#   worker     : labops-worker
#
# Multi-stage: build wheels with compilers, ship a slim runtime that runs as
# a fixed non-root UID (Kyverno policy in deploy/policies requires it).

ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim AS build
WORKDIR /src
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
COPY pyproject.toml ./
COPY labops ./labops
RUN pip wheel --wheel-dir /wheels .

FROM python:${PYTHON_VERSION}-slim AS runtime
ARG VERSION=dev
ARG GIT_SHA=unknown
LABEL org.opencontainers.image.title="labops" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.source="https://github.com/muhammadbilaljaved684-dotcom/DevOps_Projects"

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    LABOPS_STORAGE_PATH=/tmp/labops-data

RUN groupadd --system --gid 10001 labops \
 && useradd --system --uid 10001 --gid labops --no-create-home --shell /usr/sbin/nologin labops

COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels labops \
 && rm -rf /wheels

USER 10001:10001
EXPOSE 8000 9100

# Default role; overridden per Deployment.
CMD ["uvicorn", "labops.ingest_api:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]

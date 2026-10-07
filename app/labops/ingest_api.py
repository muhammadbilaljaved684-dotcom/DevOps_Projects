"""ingest-api: accept a spectrum upload, store it, enqueue a job."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from . import __version__
from .analysis import SpectrumError, parse_csv
from .db import Measurement
from .deps import Deps, build_deps
from .logging_setup import setup_logging
from .metrics import QUEUE_DEPTH, UPLOADS
from .storage import object_key

log = logging.getLogger("labops.ingest")


def create_app(deps: Deps | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        owned = app.state.deps is None
        if owned:
            app.state.deps = build_deps()
        setup_logging(app.state.deps.settings.log_level)
        yield
        if owned:
            app.state.deps.db.close()

    app = FastAPI(title="LabOps ingest API", version=__version__, lifespan=lifespan)
    app.state.deps = deps

    def d(request: Request) -> Deps:
        return request.app.state.deps

    @app.get("/healthz", response_class=PlainTextResponse)
    def healthz() -> str:
        # Liveness: the process is up. Never check dependencies here, or a
        # Redis outage would make Kubernetes restart every pod for nothing.
        return "ok"

    @app.get("/readyz", response_class=PlainTextResponse)
    def readyz(request: Request) -> str:
        deps = d(request)
        try:
            deps.db.ping()
            deps.queue.ping()
        except Exception as exc:  # noqa: BLE001 - report any dependency failure
            raise HTTPException(503, f"not ready: {exc}") from exc
        return "ready"

    @app.get("/metrics")
    def metrics(request: Request) -> PlainTextResponse:
        try:
            QUEUE_DEPTH.set(d(request).queue.depth())
        except Exception:  # noqa: BLE001 - metrics must render even if redis is down
            log.warning("could not read queue depth")
        return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.post("/api/v1/uploads", status_code=202)
    async def upload(request: Request, file: UploadFile = File(...)) -> dict:
        deps = d(request)
        raw = await file.read(deps.settings.max_upload_bytes + 1)
        if len(raw) > deps.settings.max_upload_bytes:
            UPLOADS.labels("too_large").inc()
            raise HTTPException(413, "file too large")
        try:
            parse_csv(raw)  # validate early; reject bad files with a 422
        except SpectrumError as exc:
            UPLOADS.labels("invalid").inc()
            raise HTTPException(422, str(exc)) from exc

        m = Measurement(filename=file.filename or "upload.csv", storage_key="")
        with deps.db.session() as s:
            s.add(m)
            s.flush()
            m.storage_key = object_key(m.id, m.filename)
            deps.storage.put(m.storage_key, raw)
            s.commit()
        deps.queue.put(m.id)
        UPLOADS.labels("accepted").inc()
        log.info("upload accepted", extra={"measurement_id": m.id, "role": "ingest"})
        return {"id": m.id, "status": m.status.value}

    return app


app = create_app()

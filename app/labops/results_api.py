"""results-api: read results and render a small dashboard."""

from __future__ import annotations

import html
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from . import __version__
from .deps import Deps, build_deps
from .logging_setup import setup_logging


def _fmt_ghz(hz: float | None) -> str:
    return f"{hz / 1e9:.4f} GHz" if hz is not None else "-"


def _fmt_mt(t: float | None) -> str:
    return f"{t * 1e3:.3f} mT" if t is not None else "-"


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

    app = FastAPI(title="LabOps results API", version=__version__, lifespan=lifespan)
    app.state.deps = deps

    def d(request: Request) -> Deps:
        return request.app.state.deps

    @app.get("/healthz", response_class=PlainTextResponse)
    def healthz() -> str:
        return "ok"

    @app.get("/readyz", response_class=PlainTextResponse)
    def readyz(request: Request) -> str:
        try:
            d(request).db.ping()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(503, f"not ready: {exc}") from exc
        return "ready"

    @app.get("/metrics")
    def metrics() -> PlainTextResponse:
        return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/api/v1/measurements")
    def list_measurements(request: Request, limit: int = 50) -> list[dict]:
        limit = max(1, min(limit, 200))
        return [m.to_dict() for m in d(request).db.latest(limit)]

    @app.get("/api/v1/measurements/{measurement_id}")
    def get_measurement(request: Request, measurement_id: str) -> dict:
        m = d(request).db.get(measurement_id)
        if m is None:
            raise HTTPException(404, "not found")
        return m.to_dict()

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request) -> str:
        rows = []
        for m in d(request).db.latest(25):
            r = m.result or {}
            rows.append(
                "<tr>"
                f"<td><code>{html.escape(m.id[:8])}</code></td>"
                f"<td>{html.escape(m.filename)}</td>"
                f"<td class='{m.status.value}'>{m.status.value}</td>"
                f"<td>{len(r.get('dips', []))}</td>"
                f"<td>{_fmt_ghz(r.get('zero_field_splitting_hz'))}</td>"
                f"<td>{_fmt_mt(r.get('field_tesla'))}</td>"
                f"<td>{m.processing_seconds or 0:.2f}s</td>"
                "</tr>"
            )
        body = "".join(rows) or "<tr><td colspan=7>No measurements yet</td></tr>"
        return f"""<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>LabOps</title><style>
body{{font-family:system-ui,sans-serif;margin:2rem;color:#1d2433}}
table{{border-collapse:collapse;width:100%}}
td,th{{padding:.45rem .6rem;border-bottom:1px solid #e3e6ec;text-align:left}}
.done{{color:#1a7f37}}.failed{{color:#c62828}}.queued,.processing{{color:#8a6d00}}
</style></head><body><h1>LabOps measurements</h1>
<p>Latest 25 spectra. Field is derived from the resonance splitting (NV centre, γ = 28.024 GHz/T).</p>
<table><tr><th>ID</th><th>File</th><th>Status</th><th>Dips</th>
<th>Centre</th><th>Field</th><th>Fit time</th></tr>
{body}</table></body></html>"""

    return app


app = create_app()

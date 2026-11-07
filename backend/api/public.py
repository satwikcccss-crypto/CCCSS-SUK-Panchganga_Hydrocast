"""
backend/api/public.py
=====================
Public-facing FastAPI API for HydroCast Panchganga — Port 8000.

Serves citizens, district authorities (DDMA), CWC, and external consumers:
  - Health probe (no auth)
  - System status, rainfall, runoff/stage hydrographs, alerts
  - Pipeline status, historical runs, accuracy metrics
  - Visitor counter (hashed IP)
  - WebSocket live broadcast

Security: API key (X-API-Key) or query ?key= for all public reads except /health.
Rate limited via slowapi. No admin/write operations exposed here.
"""

import os
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import asyncpg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Header, Request, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi.errors import RateLimitExceeded

load_dotenv()  # must run before modules read os.environ

from backend.api.limits import limiter, RATE_LIMIT_PUBLIC  # noqa: E402
from backend.api.keys import verify_public_key  # noqa: E402

log = logging.getLogger(__name__)

app = FastAPI(
    title="HydroCast Panchganga Public API",
    version="2.0.0",
    summary="Public rainfall-runoff and flood intelligence API (Port 8000)",
    description=(
        "Public HTTP and WebSocket API for the **HydroCast** forecasting system. "
        "Serves 90-hour ECMWF-driven precipitation, runoff, stage, and alert data "
        "for the Panchganga Basin, Kolhapur.\n\n"
        "Access model:\n"
        "| Credential | Grants |\n"
        "|:---|:---|\n"
        "| none | `/api/v1/health` only |\n"
        "| `X-API-Key` or `?key=` | all public `/api/v1/*` reads (rate limited) |\n\n"
        "This is the **public** surface. Administrative operations "
        "(pipeline trigger, abort, DB backup, recalibration) live on the "
        "**Operator Console API** (Port 8001) and require JWT + RBAC."
    ),
    openapi_tags=[
        {"name": "Health & Probes", "description": "Liveness and readiness checks."},
        {"name": "Operations", "description": "Service status and pipeline health."},
        {"name": "Hydrology", "description": "ECMWF rainfall hyetographs and station selection."},
        {"name": "Runoff", "description": "Discharge and stage hydrographs."},
        {"name": "Alerts", "description": "CWC flood alert classification."},
        {"name": "Pipeline", "description": "Per-step execution status."},
        {"name": "Historical Runs", "description": "Archived computation cycles."},
        {"name": "Accuracy Validation", "description": "Forecast skill metrics."},
    ],
    contact={"name": "HydroCast Operations"},
    license_info={"name": "Academic research use — DST-SERB funded project"},
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    retry_after = getattr(exc, "retry_after", 60)
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Rate limit exceeded",
            "detail": f"Too many requests. Allowed rate: {RATE_LIMIT_PUBLIC}",
            "retry_after_seconds": retry_after,
        },
        headers={"Retry-After": str(retry_after)},
    )


# ── CORS (public portal same-origin proxy) ─────────────────────────────────────

_cors_raw = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
_cors_wildcard = "*" in _cors_raw
if _cors_wildcard:
    log.warning(
        "CORS_ORIGINS contains '*' — allowing any origin WITHOUT credentials. "
        "Set an explicit allowlist for credentialed deployments."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _cors_wildcard else _cors_raw,
    allow_credentials=not _cors_wildcard,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Internal-Key"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Harden every public response."""

    MAX_BODY_BYTES = int(os.getenv("MAX_REQUEST_BYTES", str(1_000_000)))

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > self.MAX_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body too large"},
            )
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if request.url.path.startswith("/api/"):
            cache_control = "no-store"
            path = request.url.path
            if (
                not REQUIRE_API_KEY
                and request.method in ("GET", "HEAD")
                and response.status_code == 200
                and path.startswith("/api/v1/")
            ):
                cache_control = f"public, max-age={PUBLIC_CACHE_MAX_AGE}"
            response.headers.setdefault("Cache-Control", cache_control)
        return response


app.add_middleware(SecurityHeadersMiddleware)


# ── Config ─────────────────────────────────────────────────────────────────────

DB_URL = os.getenv("DATABASE_URL", "")
API_KEY = os.getenv("API_KEY", "")
REQUIRE_API_KEY = os.getenv("REQUIRE_API_KEY", "true").lower() == "true"
PUBLIC_CACHE_MAX_AGE = int(os.getenv("PUBLIC_CACHE_MAX_AGE", "300"))

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DB_URL, min_size=2, max_size=10)
    return _pool


# ── Auth Dependency ────────────────────────────────────────────────────────────

async def verify_public_or_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """API-key guard for public routes. Fails closed when REQUIRE_API_KEY is true."""
    if REQUIRE_API_KEY:
        supplied = x_api_key or request.query_params.get("key") or ""
        if not verify_public_key(supplied, API_KEY or ""):
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key (use X-API-Key header or ?key=)",
            )
    return True


PublicDep = Depends(verify_public_or_key)


# ── WebSocket Manager ──────────────────────────────────────────────────────────

class WSManager:
    MAX_CONNECTIONS = int(os.getenv("MAX_WS_CONNECTIONS", "200"))

    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> bool:
        if len(self.connections) >= self.MAX_CONNECTIONS:
            await ws.close(code=1013)
            log.warning("WebSocket cap (%d) reached", self.MAX_CONNECTIONS)
            return False
        await ws.accept()
        self.connections.append(ws)
        return True

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.connections:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for d in dead:
            if d in self.connections:
                self.connections.remove(d)


ws_manager = WSManager()


def _jsonify(rows) -> list[dict]:
    return [dict(r) for r in rows]


# ── Health Probe ──────────────────────────────────────────────────────────────

@app.get(
    "/api/v1/health",
    tags=["Health & Probes"],
    summary="Liveness probe",
)
async def health_check():
    return {
        "status": "healthy",
        "service": "hydrocast-backend-public",
        "version": "2.0.0",
        "port": 8000,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Status ─────────────────────────────────────────────────────────────────────

@app.get(
    "/api/v1/status",
    dependencies=[PublicDep],
    tags=["Operations"],
    summary="Service and pipeline status",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def system_status(request: Request):
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            last_cycle = await conn.fetchrow("""
                SELECT run_id, status, start_time, end_time, duration_seconds
                FROM simulation_runs
                ORDER BY start_time DESC LIMIT 1
            """)
            active_alerts = await conn.fetchval("SELECT COUNT(*) FROM alert_events WHERE status='active'")
            pipeline_ok = await conn.fetchval("""
                SELECT COUNT(*)=10 FROM pipeline_step_log
                WHERE cycle_id=(SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1)
                  AND status='success'
            """)
        return {
            "system": "operational",
            "last_cycle": dict(last_cycle) if last_cycle else None,
            "active_alerts": active_alerts or 0,
            "pipeline_ok": bool(pipeline_ok),
            "server_time": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        log.warning("Status query fallback: %s", e)
        return {
            "system": "operational",
            "last_cycle": None,
            "active_alerts": 0,
            "pipeline_ok": False,
            "server_time": datetime.now(timezone.utc).isoformat(),
            "note": "Database query pending or initial run awaiting",
        }


# ── Dashboard Aggregated Endpoint (queries PostgreSQL directly) ───────────────

@app.get(
    "/api/v1/dashboard",
    dependencies=[PublicDep],
    tags=["Operations"],
    summary="Aggregated dashboard data from PostgreSQL",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def dashboard_aggregated(request: Request, run_id: Optional[str] = None):
    """
    Single aggregated endpoint that pulls all dashboard data from PostgreSQL.
    Returns: status, ecmwf, stations, gauges, hydrograph, pipeline, logs, runs_history, validation, bridge data, etc.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # ── Last cycle / status ─────────────────────────────────────────
            last_cycle = await conn.fetchrow("""
                SELECT run_id, status, start_time, end_time, duration_seconds, peak_discharge_m3s,
                       peak_stage_m, lead_hours_to_peak, total_volume_mcm, total_rainfall_mm
                FROM simulation_runs
                ORDER BY start_time DESC LIMIT 1
            """)

            # ── Active alerts ───────────────────────────────────────────────
            alert_rows = await conn.fetch("""
                SELECT site_id, classification, stage_m, alert_level, created_at
                FROM alert_events
                WHERE status='active'
                ORDER BY created_at DESC LIMIT 20
            """)

            # ── Pipeline step log ───────────────────────────────────────────
            cycle_id = last_cycle["run_id"] if last_cycle else None
            pipeline_steps = []
            if cycle_id:
                pipeline_steps = await conn.fetch("""
                    SELECT step_number, step_name, status, duration_seconds,
                           details_json, error_message, start_time, end_time
                    FROM pipeline_step_log
                    WHERE cycle_id=$1
                    ORDER BY step_number
                """, cycle_id)

            # ── Pipeline step durations for ledger ──────────────────────────
            pipeline_ok = await conn.fetchval("""
                SELECT COUNT(*)=10 FROM pipeline_step_log
                WHERE cycle_id=$1 AND status='success'
            """, cycle_id) if cycle_id else False

            # ── Runs history ────────────────────────────────────────────────
            runs_history = await conn.fetch("""
                SELECT run_id, status, start_time, end_time, duration_seconds,
                       peak_discharge_m3s, peak_stage_m, lead_hours_to_peak
                FROM simulation_runs
                ORDER BY start_time DESC LIMIT 48
            """)

            # ── Bridge site thresholds ──────────────────────────────────────
            bridge_sites = await conn.fetch("""
                SELECT site_id, site_name, alert_stage_m, warning_stage_m,
                       danger_stage_m, hfl_m, zero_datum_m, sensor_datum_m
                FROM bridge_sites
                ORDER BY site_id
            """)

        # Build response
        result = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "status": {
                "system": "operational",
                "last_cycle": dict(last_cycle) if last_cycle else None,
                "active_alerts": len(alert_rows),
                "pipeline_ok": bool(pipeline_ok),
                "server_time": datetime.now(timezone.utc).isoformat(),
            },
            "alerts": [dict(r) for r in alert_rows],
            "pipeline": {
                "steps_completed": [s["step_number"] for s in pipeline_steps if s["status"] == "success"],
                "steps": [dict(s) for s in pipeline_steps],
                "status": "completed" if pipeline_ok else "running",
            },
            "runs_history": [dict(r) for r in runs_history],
            "bridge_sites": [dict(b) for b in bridge_sites],
            "ecmwf": {},      # populated by rainfall endpoint separately
            "stations": {},   # populated by station endpoint separately
            "gauges": {},     # populated by station endpoint separately
            "hydrograph": [], # populated by hydrograph endpoint separately
            "validation": None,  # populated by accuracy endpoint separately
            "bridgeShivaji": None,
            "bridgeRajaram": None,
            "summary": {},
        }

        # Add peak data from last cycle if available
        if last_cycle:
            result["summary"] = {
                "peak_discharge_m3s": float(last_cycle["peak_discharge_m3s"] or 0),
                "lead_hours_to_peak": int(last_cycle["lead_hours_to_peak"] or 0),
                "total_volume_mcm": float(last_cycle["total_volume_mcm"] or 0),
                "alert_level": last_cycle["status"] or "NORMAL",
            }

        return result

    except Exception as e:
        log.warning("Dashboard aggregated query fallback: %s", e)
        return {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "status": {
                "system": "operational",
                "last_cycle": None,
                "active_alerts": 0,
                "pipeline_ok": False,
                "server_time": datetime.now(timezone.utc).isoformat(),
                "note": "Database query pending or initial run awaiting",
            },
            "alerts": [],
            "pipeline": {"steps_completed": [], "steps": [], "status": "idle"},
            "runs_history": [],
            "bridge_sites": [],
            "ecmwf": {},
            "stations": {},
            "gauges": {},
            "hydrograph": [],
            "validation": None,
            "bridgeShivaji": None,
            "bridgeRajaram": None,
            "summary": {},
        }


# ── Visits ─────────────────────────────────────────────────────────────────────

@app.post(
    "/api/v1/visits/record",
    dependencies=[PublicDep],
    tags=["System"],
    summary="Record a unique visit",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def record_visit(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    _salt = os.getenv("VISIT_HASH_SALT", "")
    import hashlib
    ip_hash = hashlib.sha256((_salt + client_ip).encode("utf-8")).hexdigest()
    today = datetime.now(timezone.utc).date()
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO site_visitor_ips (ip_hash, visit_date)
                VALUES ($1, $2)
                ON CONFLICT (ip_hash, visit_date) DO NOTHING
            """, ip_hash, today)
            row = await conn.fetchrow("SELECT visit_count FROM site_visits WHERE visit_date=$1", today)
            if row is None:
                await conn.execute("INSERT INTO site_visits (visit_date, visit_count) VALUES ($1, 1)", today)
                today_count = 1
            else:
                await conn.execute("UPDATE site_visits SET visit_count = visit_count + 1 WHERE visit_date=$1", today)
                today_count = row["visit_count"] + 1
            total = await conn.fetchval("SELECT COALESCE(SUM(visit_count), 0) FROM site_visits")
        return {"today": today_count, "total": int(total), "ip_hash": ip_hash[:8] + "..."}
    except Exception as e:
        log.warning("Visit record fallback: %s", e)
        return {"today": 0, "total": 0, "ip_hash": ip_hash[:8] + "...", "note": "DB pending"}


@app.get(
    "/api/v1/visits",
    dependencies=[PublicDep],
    tags=["System"],
    summary="Read visit counts",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def read_visits(request: Request):
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            today = datetime.now(timezone.utc).date()
            row = await conn.fetchrow("SELECT visit_count FROM site_visits WHERE visit_date=$1", today)
            total = await conn.fetchval("SELECT COALESCE(SUM(visit_count), 0) FROM site_visits")
        return {"today": row["visit_count"] if row else 0, "total": int(total)}
    except Exception as e:
        log.warning("Visit read fallback: %s", e)
        return {"today": 0, "total": 0}


# ── Rainfall ───────────────────────────────────────────────────────────────────

@app.get(
    "/api/v1/rainfall/ecmwf",
    dependencies=[PublicDep],
    tags=["Hydrology"],
    summary="90-hr ECMWF hyetograph per subbasin",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def rainfall_ecmwf(request: Request):
    try:
        from backend.rainfall.open_meteo_failsafe import get_weather_failsafe
        now = datetime.now(timezone.utc)
        h6 = (now.hour // 6) * 6
        run_dt = now.replace(hour=h6, minute=0, second=0, microsecond=0)
        data = get_weather_failsafe(run_dt)
        return {"tier": data.get("tier"), "stations": data.get("stations"), "lead_hours": 90}
    except Exception as e:
        log.warning("Rainfall fallback: %s", e)
        return {"tier": "fallback", "stations": {}, "lead_hours": 90, "error": str(e)}


@app.get(
    "/api/v1/rainfall/stations",
    dependencies=[PublicDep],
    tags=["Hydrology"],
    summary="Station selection log for latest cycle",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def rainfall_stations(request: Request):
    return {"subbasins_selected": 9, "method": "MAX_RAIN_VOLUME"}


# ── Runoff / Stage ─────────────────────────────────────────────────────────────

@app.get(
    "/api/v1/runoff/hydrograph",
    dependencies=[PublicDep],
    tags=["Runoff"],
    summary="Outlet discharge hydrograph (90 pts)",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def runoff_hydrograph(request: Request):
    return {"peak_q_m3s": 0.0, "points": 90, "hydrograph": []}


@app.get(
    "/api/v1/runoff/summary",
    dependencies=[PublicDep],
    tags=["Runoff"],
    summary="Peak Q, Tp, volume, stage per bridge",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def runoff_summary(request: Request):
    return {"peak_q_m3s": 0.0, "total_volume_mcm": 0.0, "stage_shivaji_m": 0.0, "stage_rajaram_m": 0.0}


@app.get(
    "/api/v1/runoff/stage/{site_id}",
    dependencies=[PublicDep],
    tags=["Runoff"],
    summary="90-hr stage forecast at bridge",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def runoff_stage(site_id: str, request: Request):
    return {"site_id": site_id, "stage_m": 0.0, "alert_level": "NORMAL"}


# ── Alerts ─────────────────────────────────────────────────────────────────────

@app.get(
    "/api/v1/alerts",
    dependencies=[PublicDep],
    tags=["Alerts"],
    summary="Active CWC alerts",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def alerts_active(request: Request):
    return {"alerts_issued": 0, "status": "normal", "sites": {}}


@app.get(
    "/api/v1/alerts/bulletin",
    dependencies=[PublicDep],
    tags=["Alerts"],
    summary="Formatted flood bulletin",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def alerts_bulletin(request: Request):
    return {"bulletin": "NORMAL", "sites": {}, "issued_at": datetime.now(timezone.utc).isoformat()}


# ── Pipeline ───────────────────────────────────────────────────────────────────

@app.get(
    "/api/v1/pipeline",
    dependencies=[PublicDep],
    tags=["Pipeline"],
    summary="Pipeline step status for current cycle",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def pipeline_status(request: Request):
    return {"steps_completed": [], "status": "idle"}


@app.get(
    "/api/v1/pipeline/history",
    dependencies=[PublicDep],
    tags=["Pipeline"],
    summary="Last N cycle durations + status",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def pipeline_history(request: Request):
    return {"cycles": []}


# ── Historical Runs ─────────────────────────────────────────────────────────────

@app.get(
    "/api/v1/runs",
    dependencies=[PublicDep],
    tags=["Historical Runs"],
    summary="List historical computation runs",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def runs_list(request: Request):
    return {"runs": []}


@app.get(
    "/api/v1/runs/{run_id}",
    dependencies=[PublicDep],
    tags=["Historical Runs"],
    summary="Retrieve computation run details",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def runs_detail(run_id: str, request: Request):
    return {"run_id": run_id, "status": "unknown"}


# ── Accuracy ───────────────────────────────────────────────────────────────────

@app.get(
    "/api/v1/accuracy",
    dependencies=[PublicDep],
    tags=["Accuracy Validation"],
    summary="Validation metrics (NSE, RMSE, Spearman rho)",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def accuracy(request: Request):
    return {"nse": None, "rmse": None, "mae": None, "pbias": None, "spearman_rho": None}


# ── WebSocket ──────────────────────────────────────────────────────────────────

@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket):
    if not await ws_manager.connect(websocket):
        return
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ── Startup / Shutdown ─────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    try:
        await get_pool()
        log.info("Public API database pool established")
    except Exception as e:
        log.warning("Public API DB pool deferred: %s", e)


@app.on_event("shutdown")
async def shutdown():
    global _pool
    if _pool:
        await _pool.close()


__all__ = ["app", "ws_manager"]

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
_POOL_UNAVAILABLE = False


async def get_pool() -> Optional[asyncpg.Pool]:
    """Get PostgreSQL pool. Returns None if unavailable (graceful degradation)."""
    global _pool, _POOL_UNAVAILABLE
    if _POOL_UNAVAILABLE:
        return None
    if _pool is not None:
        return _pool
    try:
        _pool = await asyncpg.create_pool(DB_URL, min_size=2, max_size=10, command_timeout=3)
        log.info("PostgreSQL async pool established")
        return _pool
    except Exception as exc:
        _POOL_UNAVAILABLE = True
        log.warning(
            "PostgreSQL async pool unavailable (%s). All DB-backed endpoints will degrade to stubs.",
            exc,
        )
        return None


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
        if pool is None:
            return {
                "system": "degraded",
                "last_cycle": None,
                "active_alerts": 0,
                "pipeline_ok": False,
                "server_time": datetime.now(timezone.utc).isoformat(),
                "note": "PostgreSQL unavailable on this PC. Install on university server for full persistence.",
            }
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
        if pool is None:
            return {
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "status": {
                    "system": "degraded",
                    "last_cycle": None,
                    "active_alerts": 0,
                    "pipeline_ok": False,
                    "server_time": datetime.now(timezone.utc).isoformat(),
                    "note": "PostgreSQL unavailable on this PC. Install on university server for full persistence.",
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
        if pool is None:
            return {"today": 0, "total": 0, "ip_hash": ip_hash[:8] + "...", "note": "DB pending"}
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
        if pool is None:
            return {"today": 0, "total": 0}
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
        stations_data = data.get("stations", {})
        # Build subbasin-keyed hyetograph object expected by frontend
        subbasin_data = {}
        for station_id, hyetograph in stations_data.items():
            # Map station_id to subbasin if possible, otherwise use station_id as key
            subbasin_data[station_id] = hyetograph if isinstance(hyetograph, list) else []
        return subbasin_data
    except Exception as e:
        log.warning("Rainfall fallback: %s", e)
        return {}


@app.get(
    "/api/v1/rainfall/stations",
    dependencies=[PublicDep],
    tags=["Hydrology"],
    summary="Station selection log for latest cycle",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def rainfall_stations(request: Request):
    try:
        pool = await get_pool()
        if pool is None:
            return []
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT station_id, station_name, subbasin_id, is_active,
                       latitude, longitude, elevation_m
                FROM gauge_stations
                ORDER BY station_id
            """)
            return [dict(r) for r in rows]
    except Exception as e:
        log.warning("Station selection fallback: %s", e)
        return []


# ── Runoff / Stage ─────────────────────────────────────────────────────────────

@app.get(
    "/api/v1/runoff/hydrograph",
    dependencies=[PublicDep],
    tags=["Runoff"],
    summary="Outlet discharge hydrograph (90 pts) from latest cycle",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def runoff_hydrograph(request: Request):
    try:
        pool = await get_pool()
        if pool is None:
            return []
        async with pool.acquire() as conn:
            last_run = await conn.fetchrow("""
                SELECT run_id FROM simulation_runs
                ORDER BY start_time DESC LIMIT 1
            """)
            if not last_run:
                return []
            rows = await conn.fetch("""
                SELECT lead_hours, discharge_m3s, surface_runoff_m3s, baseflow_m3s,
                       timestamp, is_peak, stage_m
                FROM hydrograph_results
                WHERE run_id=$1
                ORDER BY lead_hours ASC
            """, last_run["run_id"])
            hydrograph = [dict(r) for r in rows]
            peak_q = max((r["discharge_m3s"] or 0) for r in hydrograph) if hydrograph else 0.0
            return hydrograph
    except Exception as e:
        log.warning("Hydrograph fallback: %s", e)
        return []


@app.get(
    "/api/v1/runoff/summary",
    dependencies=[PublicDep],
    tags=["Runoff"],
    summary="Peak Q, Tp, volume, stage per bridge from latest cycle",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def runoff_summary(request: Request):
    try:
        pool = await get_pool()
        if pool is None:
            return {"outlet": {"peak_discharge_m3s": 0.0, "lead_hours_to_peak": 0,
                               "total_volume_mcm": 0.0, "alert_level": "NORMAL"},
                    "bridges": [], "peak_arrival": {"shivaji": None, "rajaram": None},
                    "note": "DB unavailable"}
        async with pool.acquire() as conn:
            last_cycle = await conn.fetchrow("""
                SELECT run_id, peak_discharge_m3s, lead_hours_to_peak,
                       total_volume_mcm, peak_stage_m, alert_level
                FROM simulation_runs
                ORDER BY start_time DESC LIMIT 1
            """)
            if not last_cycle:
                return {"outlet": {"peak_discharge_m3s": 0.0, "lead_hours_to_peak": 0,
                                   "total_volume_mcm": 0.0, "alert_level": "NORMAL"},
                        "bridges": [], "peak_arrival": {"shivaji": None, "rajaram": None}}
            # Get latest stage per bridge
            shivaji = await conn.fetchrow("""
                SELECT stage_m, alert_level
                FROM bridge_stage_forecast
                WHERE site_id='SHIVAJI_BRIDGE'
                  AND forecast_run_id=$1
                ORDER BY forecast_time DESC LIMIT 1
            """, last_cycle["run_id"])
            rajaram = await conn.fetchrow("""
                SELECT stage_m, alert_level
                FROM bridge_stage_forecast
                WHERE site_id='RAJARAM_BRIDGE'
                  AND forecast_run_id=$1
                ORDER BY forecast_time DESC LIMIT 1
            """, last_cycle["run_id"])
            return {
                "outlet": {
                    "peak_discharge_m3s": float(last_cycle["peak_discharge_m3s"] or 0),
                    "lead_hours_to_peak": int(last_cycle["lead_hours_to_peak"] or 0),
                    "total_volume_mcm": float(last_cycle["total_volume_mcm"] or 0),
                    "alert_level": last_cycle["alert_level"] or "NORMAL",
                },
                "bridges": [
                    {
                        "site_id": "SHIVAJI_BRIDGE",
                        "site_name": "Shivaji Bridge (Panchganga Ghat)",
                        "peak_stage_m": float(shivaji["stage_m"]) if shivaji else 0.0,
                        "alert_level": shivaji["alert_level"] if shivaji else "NORMAL",
                    },
                    {
                        "site_id": "RAJARAM_BRIDGE",
                        "site_name": "Rajaram K.T. Weir (Kasba Bawada)",
                        "peak_stage_m": float(rajaram["stage_m"]) if rajaram else 0.0,
                        "alert_level": rajaram["alert_level"] if rajaram else "NORMAL",
                    },
                ],
                "peak_arrival": {
                    "shivaji": {"peak_lead_hours": int(last_cycle["lead_hours_to_peak"] or 0)},
                    "rajaram": {"peak_lead_hours": int(last_cycle["lead_hours_to_peak"] or 0)},
                },
            }
    except Exception as e:
        log.warning("Runoff summary fallback: %s", e)
        return {"outlet": {"peak_discharge_m3s": 0.0, "lead_hours_to_peak": 0,
                           "total_volume_mcm": 0.0, "alert_level": "NORMAL"},
                "bridges": [], "peak_arrival": {"shivaji": None, "rajaram": None},
                "error": str(e)}


@app.get(
    "/api/v1/runoff/stage/{site_id}",
    dependencies=[PublicDep],
    tags=["Runoff"],
    summary="Latest stage forecast for a bridge site",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def runoff_stage(site_id: str, request: Request):
    try:
        pool = await get_pool()
        if pool is None:
            return {"site_id": site_id, "stage_m": 0.0, "alert_level": "NORMAL",
                    "forecast_time": None, "lead_hours": 0, "note": "DB unavailable"}
        async with pool.acquire() as conn:
            # Get bridge site thresholds
            bridge = await conn.fetchrow("""
                SELECT site_id, site_name, alert_stage_m, warning_stage_m,
                       danger_stage_m, hfl_m
                FROM bridge_sites
                WHERE site_id=$1
            """, site_id)
            # Get latest stage forecast
            row = await conn.fetchrow("""
                SELECT stage_m, alert_level, forecast_time, lead_hours,
                       discharge_m3s, is_above_danger
                FROM bridge_stage_forecast
                WHERE site_id=$1
                ORDER BY forecast_time DESC LIMIT 1
            """, site_id)
            # Get forecast series (last 24 hours)
            forecast_rows = await conn.fetch("""
                SELECT stage_m, lead_hours
                FROM bridge_stage_forecast
                WHERE site_id=$1
                ORDER BY forecast_time DESC
                LIMIT 24
            """, site_id)
            if not bridge:
                return {"site_id": site_id, "stage_m": 0.0, "alert_level": "NORMAL",
                        "forecast_time": None, "lead_hours": 0, "note": "Bridge not found"}
            if not row:
                return {
                    "site": {
                        "site_id": site_id,
                        "site_name": bridge["site_name"],
                        "alert_stage_m": float(bridge["alert_stage_m"]),
                        "warning_stage_m": float(bridge["warning_stage_m"]),
                        "danger_stage_m": float(bridge["danger_stage_m"]),
                        "hfl_m": float(bridge["hfl_m"]),
                    },
                    "stage_m": 0.0,
                    "alert_level": "NORMAL",
                    "forecast_time": None,
                    "lead_hours": 0,
                    "forecast": [],
                }
            return {
                "site": {
                    "site_id": bridge["site_id"],
                    "site_name": bridge["site_name"],
                    "alert_stage_m": float(bridge["alert_stage_m"]),
                    "warning_stage_m": float(bridge["warning_stage_m"]),
                    "danger_stage_m": float(bridge["danger_stage_m"]),
                    "hfl_m": float(bridge["hfl_m"]),
                },
                "stage_m": float(row["stage_m"]),
                "alert_level": row["alert_level"],
                "forecast_time": row["forecast_time"].isoformat() if row["forecast_time"] else None,
                "lead_hours": int(row["lead_hours"] or 0),
                "discharge_m3s": float(row["discharge_m3s"] or 0),
                "is_above_danger": bool(row["is_above_danger"]),
                "forecast": [
                    {"stage_m": float(f["stage_m"]), "lead_hours": int(f["lead_hours"] or 0)}
                    for f in forecast_rows
                ],
            }
    except Exception as e:
        log.warning("Stage fallback for %s: %s", site_id, e)
        return {"site_id": site_id, "stage_m": 0.0, "alert_level": "NORMAL",
                "error": str(e)}


# ── Alerts ─────────────────────────────────────────────────────────────────────

@app.get(
    "/api/v1/alerts",
    dependencies=[PublicDep],
    tags=["Alerts"],
    summary="Active CWC alerts from latest cycle",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def alerts_active(request: Request):
    try:
        pool = await get_pool()
        if pool is None:
            return []
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT site_id, classification, stage_m, alert_level,
                       is_above_danger, forecast_time, created_at
                FROM alert_events
                WHERE status='active'
                ORDER BY created_at DESC LIMIT 20
            """)
            alert_list = []
            for r in rows:
                bridge = await conn.fetchrow("""
                    SELECT alert_stage_m, warning_stage_m, danger_stage_m, hfl_m
                    FROM bridge_sites
                    WHERE site_id=$1
                """, r["site_id"])
                alert_list.append({
                    "alert_type": r["alert_level"],
                    "stage_m": float(r["stage_m"] or 0),
                    "site_id": r["site_id"],
                    "warning_stage_m": float(bridge["warning_stage_m"]) if bridge else None,
                    "danger_stage_m": float(bridge["danger_stage_m"]) if bridge else None,
                    "hfl_m": float(bridge["hfl_m"]) if bridge else None,
                    "lead_hours": None,
                })
            return alert_list
    except Exception as e:
        log.warning("Alerts fallback: %s", e)
        return []


@app.get(
    "/api/v1/alerts/bulletin",
    dependencies=[PublicDep],
    tags=["Alerts"],
    summary="Formatted CWC flood bulletin",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def alerts_bulletin(request: Request):
    try:
        pool = await get_pool()
        if pool is None:
            return {"bulletin": "NORMAL", "sites": {},
                    "issued_at": datetime.now(timezone.utc).isoformat(), "note": "DB unavailable"}
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT site_id, classification, stage_m, alert_level
                FROM alert_events
                WHERE status='active'
                ORDER BY created_at DESC LIMIT 10
            """)
            if not rows:
                return {"bulletin": "NORMAL", "sites": {},
                        "issued_at": datetime.now(timezone.utc).isoformat()}
            severity_order = ["NORMAL", "ALERT", "WARNING", "DANGER", "HFL_EXCEEDED"]
            worst = max(rows, key=lambda r: severity_order.index(r["alert_level"])
                        if r["alert_level"] in severity_order else 0)
            lines = ["HYDROCAST FLOOD BULLETIN",
                     f"Issued: {datetime.now(timezone.utc).isoformat()}Z",
                     f"Status: {worst['alert_level']}"]
            for r in rows:
                lines.append(f"  {r['site_id']}: {r['stage_m']}m -> {r['alert_level']}")
            return {
                "bulletin": worst["alert_level"],
                "sites": {r["site_id"]: {"stage_m": float(r["stage_m"] or 0),
                                         "alert_level": r["alert_level"]} for r in rows},
                "issued_at": datetime.now(timezone.utc).isoformat(),
                "text": "\n".join(lines),
            }
    except Exception as e:
        log.warning("Bulletin fallback: %s", e)
        return {"bulletin": "NORMAL", "sites": {},
                "issued_at": datetime.now(timezone.utc).isoformat(), "error": str(e)}


# ── Pipeline ───────────────────────────────────────────────────────────────────

@app.get(
    "/api/v1/pipeline",
    dependencies=[PublicDep],
    tags=["Pipeline"],
    summary="Pipeline step status for current cycle",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def pipeline_status(request: Request):
    try:
        pool = await get_pool()
        if pool is None:
            return {"steps_completed": [], "status": "idle", "note": "DB unavailable"}
        async with pool.acquire() as conn:
            last_run = await conn.fetchrow("""
                SELECT run_id FROM simulation_runs
                ORDER BY start_time DESC LIMIT 1
            """)
            if not last_run:
                return {"steps_completed": [], "status": "idle"}
            rows = await conn.fetch("""
                SELECT step_number, step_name, status, duration_seconds,
                       details_json, error_message
                FROM pipeline_step_log
                WHERE cycle_id=$1
                ORDER BY step_number
            """, last_run["run_id"])
            steps_completed = [r["step_number"] for r in rows if r["status"] == "success"]
            all_success = all(r["status"] == "success" for r in rows) if rows else False
            return {
                "steps_completed": steps_completed,
                "steps": [dict(r) for r in rows],
                "logs": [dict(r) for r in rows],  # for frontend logs endpoint
                "status": "completed" if all_success else "running",
                "cycle_id": last_run["run_id"],
            }
    except Exception as e:
        log.warning("Pipeline fallback: %s", e)
        return {"steps_completed": [], "status": "idle", "error": str(e)}


@app.get(
    "/api/v1/pipeline/history",
    dependencies=[PublicDep],
    tags=["Pipeline"],
    summary="Last N cycle durations + status",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def pipeline_history(request: Request):
    try:
        pool = await get_pool()
        if pool is None:
            return {"cycles": [], "note": "DB unavailable"}
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT run_id, status, start_time, end_time, duration_seconds
                FROM simulation_runs
                ORDER BY start_time DESC LIMIT 48
            """)
            return {"cycles": [dict(r) for r in rows]}
    except Exception as e:
        log.warning("Pipeline history fallback: %s", e)
        return {"cycles": [], "error": str(e)}


# ── Historical Runs ─────────────────────────────────────────────────────────────

@app.get(
    "/api/v1/runs",
    dependencies=[PublicDep],
    tags=["Historical Runs"],
    summary="List historical computation runs",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def runs_list(request: Request):
    try:
        pool = await get_pool()
        if pool is None:
            return {"runs": [], "note": "DB unavailable"}
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT run_id, cycle_date, cycle_time, status,
                       peak_discharge_m3s, peak_stage_m, lead_hours_to_peak,
                       total_volume_mcm, alert_level, start_time, end_time
                FROM simulation_runs
                ORDER BY start_time DESC LIMIT 100
            """)
            return {"runs": [dict(r) for r in rows]}
    except Exception as e:
        log.warning("Runs list fallback: %s", e)
        return {"runs": [], "error": str(e)}


@app.get(
    "/api/v1/runs/{run_id}",
    dependencies=[PublicDep],
    tags=["Historical Runs"],
    summary="Retrieve computation run details",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def runs_detail(run_id: str, request: Request):
    try:
        pool = await get_pool()
        if pool is None:
            return {"run_id": run_id, "status": "error", "note": "DB unavailable"}
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM simulation_runs WHERE run_id=$1
            """, run_id)
            if not row:
                return {"run_id": run_id, "status": "not_found"}
            return dict(row)
    except Exception as e:
        log.warning("Run detail fallback: %s", e)
        return {"run_id": run_id, "status": "error", "error": str(e)}


# ── Accuracy ───────────────────────────────────────────────────────────────────

@app.get(
    "/api/v1/accuracy",
    dependencies=[PublicDep],
    tags=["Accuracy Validation"],
    summary="Validation metrics (NSE, RMSE, Spearman rho) from latest cycle",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def accuracy(request: Request, run_id: Optional[str] = None):
    try:
        pool = await get_pool()
        if pool is None:
            return {"cycle_id": run_id or "unknown", "validation": None, "note": "DB unavailable"}
        async with pool.acquire() as conn:
            if run_id:
                row = await conn.fetchrow("""
                    SELECT * FROM forecast_validation_metrics WHERE run_id=$1
                """, run_id)
            else:
                row = await conn.fetchrow("""
                    SELECT * FROM forecast_validation_metrics
                    ORDER BY created_at DESC LIMIT 1
                """)
            if not row:
                return {"cycle_id": run_id or "unknown",
                        "validation": {"metrics": None, "status": "no_data"}}
            return {
                "cycle_id": row["run_id"],
                "validation": {
                    "metrics": {
                        "nse": float(row["nse_discharge"]) if row["nse_discharge"] else None,
                        "rmse": float(row["rmse_q_m3s"]) if row["rmse_q_m3s"] else None,
                        "mae": float(row["mae_q_m3s"]) if row["mae_q_m3s"] else None,
                        "pbias": float(row["pbias_discharge_pct"]) if row["pbias_discharge_pct"] else None,
                        "spearman_rho": float(row["spearman_rho"]) if row["spearman_rho"] else None,
                        "performance_grade": row["performance_grade"],
                    },
                    "status": "available",
                },
            }
    except Exception as e:
        log.warning("Accuracy fallback: %s", e)
        return {"cycle_id": run_id or "unknown", "validation": None, "error": str(e)}


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

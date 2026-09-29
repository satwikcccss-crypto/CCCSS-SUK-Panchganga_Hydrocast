"""
Rainfall-Runoff System — FastAPI Backend
=========================================
Serves all hydrologic data to:
  - Next.js dashboard (same-host or CORS)
  - External consumers via API key and rate-limited public endpoints
  - Disaster management authority administrative endpoints via JWT

Run: uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4

Endpoints
---------
GET /api/v1/health                  health check for Docker & probes
GET /api/v1/status                  system health + current cycle info
GET /api/v1/rainfall/ecmwf          90-hr ECMWF hyetograph per subbasin
GET /api/v1/rainfall/stations       station selection log for latest cycle
GET /api/v1/rainfall/gauges         all raw gauge hyetographs (last cycle)
GET /api/v1/runoff/hydrograph       outlet discharge hydrograph (90 pts)
GET /api/v1/runoff/summary          peak Q, Tp, volume, stage per bridge
GET /api/v1/runoff/stage/{site_id}  90-hr stage forecast at bridge
GET /api/v1/alerts                  active CWC alerts
GET /api/v1/alerts/bulletin         formatted flood bulletin (PDF-ready JSON)
GET /api/v1/pipeline                pipeline step status for current cycle
GET /api/v1/pipeline/history        last N cycle durations + status
GET /api/v1/runs                    list historical computation runs
GET /api/v1/runs/{run_id}           retrieve computation run details
GET /api/v1/accuracy                validation metrics (NSE, RMSE, Spearman rho)
POST /api/v1/admin/auth/token       admin JWT login
POST /api/v1/admin/trigger-run      manual pipeline cycle trigger
POST /api/v1/admin/archive          cold storage parquet archival
WS  /ws/live                        WebSocket: push on each new cycle result
"""

import os
import hmac
import json
import asyncio
import logging
import hashlib
from datetime import datetime, timezone
from typing import Optional, Any

import asyncpg
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Header, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.api.admin import router as admin_router

log = logging.getLogger(__name__)

# ── Rate Limiter Initialization (slowapi) ─────────────────────────────────────
RATE_LIMIT_PUBLIC = os.getenv("RATE_LIMIT_PUBLIC", "100/minute")
limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT_PUBLIC])

app = FastAPI(
    title="HydroCast Panchganga Operational API",
    version="2.0.0",
    summary="Rainfall-runoff and river flood intelligence for the Panchganga Basin, Kolhapur.",
    description=(
        "Operational HTTP and WebSocket API for the **HydroCast** rainfall-runoff "
        "forecasting system.\n\n"
        "It serves a 90-hour forecast horizon driven by ECMWF IFS quantitative "
        "precipitation forecasts over the Panchganga Basin. Nine gauged subbasins "
        "feed an SCS-CN loss / SCS unit-hydrograph / Muskingum cascade "
        "(R1–R5), whose outlet discharge is converted to river stage through a "
        "WRD-anchored PCHIP rating curve at two bridge sites.\n\n"
        "### How to use this reference\n"
        "Everything on this page is generated from the route declarations in "
        "`src/api/main.py` and `src/api/admin.py`. Use **Authorize** in the top "
        "right corner to attach an `X-API-Key` header for public routes, or a JWT "
        "bearer token for administrative routes, then use **Try it out** to call "
        "the live deployment.\n\n"
        "### Access model\n"
        "| Credential | Grants |\n"
        "|:---|:---|\n"
        "| none | `/api/v1/health` only |\n"
        "| `X-API-Key` | all public `/api/v1/*` reads (rate limited) |\n"
        "| JWT (HS256) | `/api/v1/admin/*` — trigger runs, archive, recalibrate |\n"
        "| `X-Internal-Key` | internal broadcast, hidden from this reference |\n\n"
        "### Related documentation\n"
        "* Architecture Atlas — end-to-end system diagrams\n"
        "* Real-Time Runoff Modelling — the hydrology behind the numbers\n"
        "* HEC-HMS Emulator — the calibrated routing engine\n"
        "* API Reference — Python source reference for every module\n\n"
        "Every response time is in **UTC** unless stated otherwise. Discharge is "
        "in **m³/s**, rainfall in **mm/hr**, and stage in **metres above mean sea "
        "level** on the WRD datum."
    ),
    openapi_tags=[
        {"name": "Health & Probes", "description": "Liveness and readiness checks for container orchestration."},
        {"name": "Operations", "description": "Service status, current cycle identity, and pipeline health."},
        {"name": "System", "description": "Anonymous dashboard usage counters."},
        {"name": "Hydrology", "description": "Forecast and observed precipitation: ECMWF areal hyetographs, station selection decisions, raw gauge records."},
        {"name": "Runoff", "description": "Forecast discharge, stage, and the live calibration parameters that produced them."},
        {"name": "Alerts", "description": "Flood alert classification and CWC/DDMA bulletin payloads."},
        {"name": "Pipeline", "description": "Per-step execution status of the 12-step forecast cycle."},
        {"name": "Historical Runs", "description": "Paginated ledger of archived computation cycles."},
        {"name": "Accuracy Validation", "description": "Forecast skill metrics with explicit sample-size gates."},
        {"name": "Admin", "description": "Authenticated operations: manual triggering, cold-storage archival, and forced ML recalibration."},
    ],
    contact={"name": "HydroCast Operations", "url": "https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast"},
    license_info={"name": "Academic research use — DST-SERB funded project"},
)

app.state.limiter = limiter

# Rate limit exception handler with RFC-standard Retry-After header
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Mount Administrative & Control Router (protected by JWT & API Key)
app.include_router(admin_router)

DB_URL = os.getenv("DATABASE_URL", "")
API_KEY = os.getenv("API_KEY", "")
REQUIRE_API_KEY = os.getenv("REQUIRE_API_KEY", "true").lower() == "true"

# ── DB pool (asyncpg) ─────────────────────────────────────────────────────────

_pool: asyncpg.Pool | None = None

async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DB_URL, min_size=2, max_size=10)
    return _pool

telegram_app = None

@app.on_event("startup")
async def startup():
    try:
        pool = await get_pool()
        log.info("Database connection pool established")
        
        # Init Visitor Counter Tables
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS site_visits (
                    visit_date DATE PRIMARY KEY,
                    visit_count INT DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS site_visitor_ips (
                    ip_hash TEXT,
                    visit_date DATE,
                    PRIMARY KEY(ip_hash, visit_date)
                );
            """)
    except Exception as e:
        log.warning("Database pool connection delayed or offline: %s", e)

    try:
        from src.alerts.telegram_bot import build_telegram_application
        global telegram_app
        telegram_app = build_telegram_application()
        if telegram_app:
            await telegram_app.initialize()
            await telegram_app.start()
            await telegram_app.updater.start_polling()
            log.info("Telegram Bot started successfully")
    except Exception as e:
        log.warning(f"Telegram Bot failed to start: {e}")

@app.on_event("shutdown")
async def shutdown():
    if _pool:
        await _pool.close()
    if telegram_app:
        try:
            await telegram_app.updater.stop()
            await telegram_app.stop()
            await telegram_app.shutdown()
            log.info("Telegram Bot stopped")
        except Exception as e:
            log.error(f"Error stopping Telegram Bot: {e}")


# ── Auth & Dependencies ───────────────────────────────────────────────────────

async def verify_public_or_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """
    If REQUIRE_API_KEY is True, enforce X-API-Key validation.
    Otherwise, permit access (protected by IP rate-limiting).
    """
    if REQUIRE_API_KEY:
        if not x_api_key or x_api_key != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")
    return True

PublicDep = Depends(verify_public_or_key)


# ── WebSocket manager ─────────────────────────────────────────────────────────

class WSManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _jsonify(rows) -> list[dict]:
    return [dict(r) for r in rows]


# ── Health Probe ──────────────────────────────────────────────────────────────

@app.get(
    "/api/v1/health",
    tags=["Health & Probes"],
    summary="Liveness probe",
    response_description="Service identity, version, and current UTC time.",
)
async def health_check():
    """Liveness probe for Docker healthchecks and monitoring.

    The only endpoint that requires no credential. It touches no database and no
    external service, so a `200` here means *the process is up* — not that the
    forecast pipeline is healthy. Use `/api/v1/status` for pipeline state.
    """
    return {
        "status": "healthy",
        "service": "hydrocast-backend",
        "version": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Operational Endpoints ─────────────────────────────────────────────────────

@app.get(
    "/api/v1/status",
    dependencies=[PublicDep],
    tags=["Operations"],
    summary="Service and pipeline status",
    response_description="Latest cycle record, active alert count, and a 10-of-10 pipeline completion flag.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def system_status(request: Request):
    """Report service status together with the most recent computation cycle.

    `pipeline_ok` is `true` only when **all 10** logged pipeline steps for the
    latest cycle carry `status='success'`.

    If the database is unreachable or no cycle has run yet, the endpoint
    degrades gracefully rather than raising: it returns `pipeline_ok: false`
    with an explanatory `note` instead of a `500`.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            last_cycle = await conn.fetchrow("""
                SELECT run_id, status, start_time, end_time, duration_seconds
                FROM simulation_runs
                ORDER BY start_time DESC LIMIT 1
            """)
            active_alerts = await conn.fetchval("SELECT COUNT(*) FROM alert_events WHERE status='active'")
            pipeline_ok   = await conn.fetchval("""
                SELECT COUNT(*)=10 FROM pipeline_step_log
                WHERE cycle_id=(SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1)
                  AND status='success'
            """)
        return {
            "system":         "operational",
            "last_cycle":     dict(last_cycle) if last_cycle else None,
            "active_alerts":  active_alerts or 0,
            "pipeline_ok":    bool(pipeline_ok),
            "server_time":    datetime.now(timezone.utc).isoformat(),
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


@app.post(
    "/api/v1/visits/record",
    dependencies=[PublicDep],
    tags=["System"],
    summary="Record a unique visit",
    response_description="Unique-visitor counts for today and for all time.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def record_visit(request: Request):
    """Records a unique visit and returns today's and total visitor counts.

    The client IP is SHA-256 hashed before it touches the database — the raw
    address is never stored. De-duplication is per UTC day, so a repeat call
    from the same address on the same day increments nothing.
    """
    client_ip = request.client.host if request.client else "unknown"
    ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM site_visitor_ips WHERE ip_hash=$1 AND visit_date=CURRENT_DATE",
            ip_hash
        )
        if not exists:
            await conn.execute(
                "INSERT INTO site_visitor_ips (ip_hash, visit_date) VALUES ($1, CURRENT_DATE)",
                ip_hash
            )
            await conn.execute("""
                INSERT INTO site_visits (visit_date, visit_count)
                VALUES (CURRENT_DATE, 1)
                ON CONFLICT (visit_date) DO UPDATE SET visit_count = site_visits.visit_count + 1
            """)
        
        daily = await conn.fetchval("SELECT visit_count FROM site_visits WHERE visit_date=CURRENT_DATE")
        total = await conn.fetchval("SELECT SUM(visit_count) FROM site_visits")
        
    return {"daily": daily or 0, "total": total or 0}


@app.get(
    "/api/v1/rainfall/ecmwf",
    dependencies=[PublicDep],
    tags=["Hydrology"],
    summary="ECMWF areal hyetograph per subbasin",
    response_description="A map of subbasin id to its 90-point hourly rainfall series (mm/hr).",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def ecmwf_hyetograph(request: Request, subbasin_id: Optional[str] = None):
    """90-hr ECMWF IFS areal rainfall per subbasin (mm/hr, hourly).

    Always reads the **latest** `forecast_run_time` for `source_id='ecmwf_ifs'`,
    so repeated calls never mix two cycles.

    :param subbasin_id: Optional filter. Omit it to return all nine subbasins.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        query = """
            SELECT subbasin_id, valid_time, lead_hours, rainfall_mm_hr
            FROM subbasin_rainfall_ts
            WHERE source_id='ecmwf_ifs'
              AND forecast_run_time = (
                  SELECT MAX(forecast_run_time) FROM subbasin_rainfall_ts WHERE source_id='ecmwf_ifs'
              )
            AND ($1::text IS NULL OR subbasin_id=$1)
            ORDER BY subbasin_id, lead_hours
        """
        rows = await conn.fetch(query, subbasin_id)

    result: dict[str, list] = {}
    for r in rows:
        sub = r["subbasin_id"]
        result.setdefault(sub, []).append({
            "hour":    r["lead_hours"],
            "time":    r["valid_time"].isoformat(),
            "mm_hr":   r["rainfall_mm_hr"],
        })
    return result


@app.get(
    "/api/v1/rainfall/stations",
    dependencies=[PublicDep],
    tags=["Hydrology"],
    summary="Station selection decisions for the latest cycle",
    response_description="One row per subbasin: the governing gauge, its cumulative rainfall, and the full candidate set.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def station_selection(request: Request):
    """Selection decision for each subbasin in the latest cycle.

    Selection is **database-first**: if a subbasin's governing station has
    readings in the last 90 hours it wins; otherwise the selector falls back to
    the nearest grid cell. `all_candidates_json` carries every station that was
    considered with its distance rank, so a decision can always be audited
    after the fact.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT s.subbasin_id, s.selected_station_id, s.cumulative_mm,
                   s.all_candidates_json, s.selected_at,
                   g.station_name, ST_Y(g.geom) lat, ST_X(g.geom) lon
            FROM station_selection_log s
            JOIN gauge_stations g ON g.station_id=s.selected_station_id
            WHERE s.cycle_id=(SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1)
            ORDER BY s.subbasin_id
        """)
    return _jsonify(rows)


@app.get(
    "/api/v1/rainfall/gauges",
    dependencies=[PublicDep],
    tags=["Hydrology"],
    summary="Raw gauge hyetographs",
    response_description="Every individual gauge record from the last 91 hours, with quality flags and coordinates.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def gauge_hyetographs(request: Request):
    """All individual gauge 90-hr hyetographs for the latest cycle.

    Unlike [`/api/v1/rainfall/ecmwf`](#api-v1-rainfall-ecmwf) — which returns
    the *areal* rainfall chosen per subbasin — this endpoint returns the raw
    per-gauge series for all 18 stations. Use it to audit why a particular
    station was selected.

    `quality_flag` propagates upstream sensor quality and is never filtered
    out; consumers should honour it rather than assuming every row is equally
    trustworthy.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT r.gauge_id, r.subbasin_id, r.timestamp,
                   r.rainfall_mm, r.quality_flag,
                   g.station_name, ST_Y(g.geom) lat, ST_X(g.geom) lon
            FROM rainfall_data r
            JOIN gauge_stations g ON g.station_id=r.gauge_id
            WHERE r.timestamp >= NOW()-'91 hours'::interval
            ORDER BY r.gauge_id, r.timestamp
        """)
    return _jsonify(rows)


@app.get(
    "/api/v1/runoff/hydrograph",
    dependencies=[PublicDep],
    tags=["Runoff"],
    summary="Outlet discharge hydrograph",
    response_description="90 points of total, surface, and baseflow discharge with stage and peak flags.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def outlet_hydrograph(request: Request, outlet_node: str = "J_Outlet"):
    """90-hr discharge + stage at the sink outlet node.

    The response separates the two physical components so a consumer can reason
    about them separately:

    * `discharge_m3s` — total discharge
    * `surface_runoff_m3s` — the routed surface component from SCS-CN + UH
    * `baseflow_m3s` — exponential recession, floored at the WRD monsoon value
    * `stage_m` — the same discharge pushed through the PCHIP rating curve
    * `is_peak` — `true` on the single `argmax` of total discharge
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT timestamp, lead_hours, discharge_m3s,
                   surface_runoff_m3s, baseflow_m3s, stage_m, is_peak
            FROM v_latest_hydrograph
            WHERE outlet_node=$1
            ORDER BY timestamp
        """, outlet_node)
    return _jsonify(rows)


@app.get(
    "/api/v1/runoff/summary",
    dependencies=[PublicDep],
    tags=["Runoff"],
    summary="Peak discharge summary with arrival confidence",
    response_description="Outlet peak statistics, per-bridge forecast series, peak arrival window, and calibration state.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def runoff_summary(request: Request):
    """Peak Q, Tp, volume, flood alert for the latest run with peak arrival confidence intervals.

    The response has four independent parts:

    * `outlet` — peak discharge, time of peak, and runoff volume at the sink
    * `bridges` — the full stage series at each bridge with its thresholds
    * `peak_arrival` — a calibrated window around the predicted time of peak
    * `recalibration` — the live calibration state, so a consumer can always
      tell *which parameters* produced the numbers it is looking at

    `peak_arrival` is reported separately from the point estimate on purpose:
    the arrival window carries real uncertainty, and collapsing it to a single
    timestamp would overstate the precision of the forecast.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT * FROM v_latest_peak_summary
            WHERE outlet_node='J_Outlet'
        """)
        bridge_rows = await conn.fetch("""
            SELECT f.site_id, f.forecast_time, f.stage_m,
            f.discharge_m3s, f.alert_level, f.arrival_time,
            b.warning_stage_m, b.danger_stage_m, b.hfl_m
            FROM bridge_stage_forecast f
            JOIN bridge_sites b ON b.site_id=f.site_id
            WHERE f.forecast_run_id=(SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1)
            ORDER BY f.site_id, f.forecast_time
        """)

    # Attach calibrated peak arrival windows from latest state
    from src.hydrology.runs_tracker import list_computation_runs
    from src.hydrology.ml_calibration import calibrator
    latest_runs = list_computation_runs(limit=1)
    peak_arrival = None
    if latest_runs:
        peak_arrival = latest_runs[0].get("summary", {}).get("peak_arrival")

    return {
        "outlet":  dict(row) if row else None,
        "bridges": _jsonify(bridge_rows),
        "peak_arrival": peak_arrival,
        "recalibration": calibrator.state,
    }


@app.get(
    "/api/v1/runoff/calibration",
    dependencies=[PublicDep],
    tags=["Runoff"],
    summary="Live calibration parameters",
    response_description="Current Curve Number, Muskingum K/X, and subbasin lag with the calibrator's own state.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def hydrologic_calibration(request: Request):
    """Current real-time calibrated hydrologic parameters (Muskingum K & X, Subbasin lag, Curve Number).

    Exposing these makes every forecast self-describing: any client can record
    which parameters produced a given run, so a forecast can be reproduced or
    challenged later.

    The values here are read back from `Basin_1.basin`, which is the single
    source of truth. Recalibration writes that file atomically and keeps a
    timestamped `.bak` alongside it.
    """
    from src.hydrology.ml_calibration import calibrator
    return {
        "calibration": calibrator.state,
        "status": "OPERATIONAL",
    }


@app.get(
    "/api/v1/runoff/stage/{site_id}",
    dependencies=[PublicDep],
    tags=["Runoff"],
    summary="Stage forecast at a bridge site",
    response_description="Bridge metadata (thresholds and datum) plus the 90-hour stage and alert series.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def bridge_stage_forecast(request: Request, site_id: str):
    """90-hr stage + alert classification at a bridge site.

    Returns the site's own metadata alongside the series, including the
    `alert`, `warning`, `danger` and `hfl` stage marks, so a consumer never has
    to hard-code thresholds to classify a stage.

    :raises HTTPException 404: if `site_id` is not a known bridge.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT f.forecast_time, f.lead_hours, f.stage_m,
                   f.discharge_m3s, f.alert_level, f.is_above_danger
            FROM bridge_stage_forecast f
            WHERE f.site_id=$1
              AND f.forecast_run_id=(SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1)
            ORDER BY f.lead_hours
        """, site_id)
        meta = await conn.fetchrow(
            "SELECT * FROM bridge_sites WHERE site_id=$1", site_id
        )
    if not meta:
        raise HTTPException(status_code=404, detail=f"Bridge site '{site_id}' not found")
    return {
        "site":     dict(meta),
        "forecast": _jsonify(rows),
    }


@app.get(
    "/api/v1/alerts",
    dependencies=[PublicDep],
    tags=["Alerts"],
    summary="Active flood alerts",
    response_description="Every alert currently in the active state, enriched with bridge and threshold context.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def active_alerts(request: Request):
    """List active flood warnings and CWC notifications.

    Only alerts with `status='active'` are returned. Resolved alerts remain
    queryable through the historical runs ledger, so nothing is lost by
    filtering here.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM v_active_alerts_enriched")
    return _jsonify(rows)


@app.get(
    "/api/v1/alerts/bulletin",
    dependencies=[PublicDep],
    tags=["Alerts"],
    summary="CWC/DDMA flood bulletin payload",
    response_description="A print-ready bulletin per bridge: current stage, trend, HFL margin, and recommended action.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def flood_bulletin(request: Request):
    """Generate CWC-style flood bulletin JSON for all bridge sites.

    Includes: current stage, trend, HFL margin, recommended action.

    This is the payload the Telegram dispatcher forwards to district officers,
    so it is shaped for human reading rather than for plotting — the same data
    in a charting-friendly form is available from
    [`/api/v1/runoff/summary`](#api-v1-runoff-summary).
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT b.site_id, b.site_name,
                   b.alert_stage_m, b.warning_stage_m, b.danger_stage_m, b.hfl_m,
                   f.stage_m AS current_stage,
                   f.discharge_m3s AS current_q,
                   f.alert_level,
                   f.arrival_time,
                   p.peak_discharge_m3s,
                   p.time_of_peak,
                   p.total_runoff_volume_m3
            FROM bridge_sites b
            LEFT JOIN bridge_stage_forecast f ON f.site_id=b.site_id
                AND f.lead_hours=1
                AND f.forecast_run_id=(SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1)
            LEFT JOIN peak_discharge_events p ON p.outlet_node='J_Outlet'
                AND p.run_id=(SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1)
            ORDER BY b.site_id
        """)
    issued_at = datetime.now(timezone.utc).isoformat()
    return {
        "bulletin_title": "CWC CENTRAL WATER COMMISSION — FLOOD BULLETIN",
        "issued_at":      issued_at,
        "valid_for_hrs":  90,
        "sites":          _jsonify(rows),
    }


@app.get(
    "/api/v1/pipeline",
    dependencies=[PublicDep],
    tags=["Pipeline"],
    summary="Current cycle step status",
    response_description="Per-step status of the latest cycle, plus 7-day completion/failure counts and mean duration.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def pipeline_status(request: Request):
    """Current cycle pipeline step statuses.

    `error_message` is populated only for failed steps, which is the fastest
    way to tell *where* a cycle broke as well as *that* it broke.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT step_number, step_name, status, start_time, end_time,
                   duration_seconds, error_message
            FROM pipeline_step_log
            WHERE cycle_id=(SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1)
            ORDER BY step_number
        """)
        metrics = await conn.fetchrow("""
            SELECT COUNT(*) FILTER (WHERE status='completed') AS completed,
                   COUNT(*) FILTER (WHERE status='failed')    AS failed,
                   AVG(duration_seconds)                       AS avg_duration_s
            FROM simulation_runs
            WHERE start_time > NOW()-'7 days'::interval
        """)
    return {
        "steps":   _jsonify(rows),
        "metrics": dict(metrics) if metrics else {},
    }


@app.get(
    "/api/v1/pipeline/history",
    dependencies=[PublicDep],
    tags=["Pipeline"],
    summary="Recent cycle performance",
    response_description="Newest-first list of cycle durations and execution statuses.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def cycle_history(request: Request, limit: int = 48):
    """Last N cycle summaries.

    :param limit: How many cycles to return. Defaults to 48 — twelve days at
        the production cadence of four cycles per day.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM v_cycle_performance
            ORDER BY start_time DESC
            LIMIT $1
        """, limit)
    return _jsonify(rows)


# ── Historical Runs & Accuracy Validation Endpoints ───────────────────────────

@app.get(
    "/api/v1/runs",
    dependencies=[PublicDep],
    tags=["Historical Runs"],
    summary="List historical computation runs",
    response_description="Newest-first run summaries with KPIs and an accuracy rollup.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def list_runs(request: Request, limit: int = 50):
    """List all tracked historical computation runs with KPIs & accuracy summary.

    :param limit: Maximum number of runs to return. Defaults to 50.
    """
    try:
        from src.hydrology.runs_tracker import list_computation_runs
        return list_computation_runs(limit=limit)
    except Exception as e:
        log.warning("Failed to list runs: %s", e)
        return []


@app.get(
    "/api/v1/runs/{run_id}",
    dependencies=[PublicDep],
    tags=["Historical Runs"],
    summary="Retrieve one archived run",
    response_description="The complete archived payload for a single simulation cycle.",
    responses={404: {"description": "No run exists with that identifier."}},
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def get_run_details(request: Request, run_id: str):
    """Retrieve full computation payload for a specific historical run.

    :raises HTTPException 404: if `run_id` is not present in the run ledger.
    """
    from src.hydrology.runs_tracker import get_computation_run
    run = get_computation_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return run


@app.get(
    "/api/v1/accuracy",
    dependencies=[PublicDep],
    tags=["Accuracy Validation"],
    summary="Forecast skill metrics",
    response_description="Skill metrics with the sample-size gates that decided which of them could be computed.",
    responses={404: {"description": "No computation run is available to validate."}},
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def forecast_accuracy(request: Request, run_id: Optional[str] = None):
    """Compute forecast skill for a run.

    Returns Spearman rank correlation, Pearson R², NSE, RMSE, MAE, and
    18-station rainfall volume accuracy.

    ### Why some metrics may be missing

    Metrics are gated on evidence, not reported optimistically:

    * **Error metrics** (RMSE, MAE, PBIAS) are always computable — they need
      only the pairs that exist.
    * **Skill metrics** (NSE, ρ, r²) additionally require at least 6 matched
      hours, a non-degenerate observed series (σ ≥ 0.05 m), and non-zero
      squared deviations (Σ(O−Ō)² > 1e-4). Below those thresholds they are
      omitted with an explicit reason rather than returned as a number that
      would look meaningful but be meaningless.

    Observed "discharge" here is observed **stage** passed through the same
    rating curve that generated the forecast, and is labelled
    `RATING_IMPLIED_DERIVED` accordingly — it is a monotone transform of the
    stage error, not independent evidence of discharge skill.

    :param run_id: Evaluate this run. Defaults to the most recent one.
    """
    from src.hydrology.runs_tracker import list_computation_runs, get_computation_run
    from src.hydrology.validation_metrics import evaluate_forecast_accuracy

    if run_id:
        run = get_computation_run(run_id)
    else:
        runs = list_computation_runs(limit=1)
        run = get_computation_run(runs[0]["cycle_id"]) if runs else None

    if not run:
        raise HTTPException(status_code=404, detail="No computation runs available for validation")

    val = run.get("validation")
    if not val or not val.get("metrics"):
        val = evaluate_forecast_accuracy(run)
    return {
        "cycle_id": run.get("cycle_id"),
        "run_date": run.get("summary", {}).get("forecast_date"),
        "validation": val,
    }


# ── WebSocket live push ────────────────────────────────────────────────────────

@app.websocket(
    "/ws/live",
    name="live_cycle_push",
)
async def ws_live(websocket: WebSocket):
    """Push new data to connected dashboards after each completed cycle.

    The pipeline orchestrator calls `ws_manager.broadcast()` after step 12.
    Dead connections are detected on send and reaped automatically, so a
    browser that vanishes mid-cycle does not block the remaining subscribers.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.post("/internal/broadcast", include_in_schema=False)
async def internal_broadcast(payload: dict, x_internal_key: str = Header(None)):
    """Called by orchestrator after each successful cycle. Not public."""
    _ik = os.getenv("INTERNAL_KEY", "")
    if not _ik or not hmac.compare_digest(str(x_internal_key or ""), _ik):
        raise HTTPException(status_code=403, detail="Invalid internal key")
    await ws_manager.broadcast(payload)
    return {"broadcast_to": len(ws_manager.connections)}

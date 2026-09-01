"""
Rainfall-Runoff System — FastAPI Backend
=========================================
Serves all data to:
  - Next.js dashboard (same-host or CORS)
  - External consumers via API key

Run: uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4

Endpoints
---------
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
WS  /ws/live                        WebSocket: push on each new cycle result
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Any

import asyncpg
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

log = logging.getLogger(__name__)

app = FastAPI(
    title="HydroForecast API",
    version="2.0.0",
    description="Real-time rainfall-runoff prediction for Godavari basin",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

DB_URL = os.getenv("DATABASE_URL", "postgresql://hms_app:password@localhost:5432/rainfall_runoff")
API_KEY = os.getenv("API_KEY", "CHANGE_ME")

# ── DB pool (asyncpg) ─────────────────────────────────────────────────────────

_pool: asyncpg.Pool | None = None

async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DB_URL, min_size=2, max_size=10)
    return _pool

@app.on_event("startup")
async def startup():
    await get_pool()
    log.info("Database pool ready")

@app.on_event("shutdown")
async def shutdown():
    if _pool:
        await _pool.close()


# ── Auth ──────────────────────────────────────────────────────────────────────

async def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")

PublicDep = None          # no auth for dashboard
ExternalDep = Depends(verify_api_key)


# ── WebSocket manager ─────────────────────────────────────────────────────────

class WSManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        self.connections.discard(ws) if hasattr(self.connections, "discard") \
            else self.connections.remove(ws) if ws in self.connections else None

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.connections:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for d in dead:
            self.connections.remove(d)

ws_manager = WSManager()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _jsonify(rows) -> list[dict]:
    return [dict(r) for r in rows]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/v1/status")
async def system_status():
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
        "active_alerts":  active_alerts,
        "pipeline_ok":    pipeline_ok,
        "server_time":    datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/rainfall/ecmwf")
async def ecmwf_hyetograph(subbasin_id: Optional[str] = None):
    """90-hr ECMWF IFS areal rainfall per subbasin (mm/hr, hourly)."""
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

    # Group by subbasin
    result: dict[str, list] = {}
    for r in rows:
        sub = r["subbasin_id"]
        result.setdefault(sub, []).append({
            "hour":    r["lead_hours"],
            "time":    r["valid_time"].isoformat(),
            "mm_hr":   r["rainfall_mm_hr"],
        })
    return result


@app.get("/api/v1/rainfall/stations")
async def station_selection():
    """Selection decision for each subbasin in the latest cycle."""
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


@app.get("/api/v1/rainfall/gauges")
async def gauge_hyetographs():
    """All individual gauge 90-hr hyetographs for the latest cycle."""
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


@app.get("/api/v1/runoff/hydrograph")
async def outlet_hydrograph(outlet_node: str = "J_Outlet"):
    """90-hr discharge + stage at the sink outlet node."""
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


@app.get("/api/v1/runoff/summary")
async def runoff_summary():
    """Peak Q, Tp, volume, flood alert for the latest run."""
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
    return {
        "outlet":  dict(row) if row else None,
        "bridges": _jsonify(bridge_rows),
    }


@app.get("/api/v1/runoff/stage/{site_id}")
async def bridge_stage_forecast(site_id: str):
    """90-hr stage + alert classification at a bridge site."""
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


@app.get("/api/v1/alerts")
async def active_alerts():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM v_active_alerts_enriched")
    return _jsonify(rows)


@app.get("/api/v1/alerts/bulletin")
async def flood_bulletin():
    """
    Generate CWC-style flood bulletin JSON for all bridge sites.
    Includes: current stage, trend, HFL margin, recommended action.
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


@app.get("/api/v1/pipeline")
async def pipeline_status():
    """Current cycle pipeline step statuses."""
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


@app.get("/api/v1/pipeline/history")
async def cycle_history(limit: int = 48):
    """Last N cycle summaries."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM v_cycle_performance
            ORDER BY start_time DESC
            LIMIT $1
        """, limit)
    return _jsonify(rows)


# ── WebSocket live push ────────────────────────────────────────────────────────

@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket):
    """
    Push new data to connected dashboards after each completed cycle.
    The pipeline orchestrator calls ws_manager.broadcast() after step 8.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()   # keep alive / handle pings
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.post("/internal/broadcast", include_in_schema=False)
async def internal_broadcast(payload: dict, x_internal_key: str = Header(None)):
    """Called by orchestrator after each successful cycle. Not public."""
    if x_internal_key != os.getenv("INTERNAL_KEY", "internal_secret"):
        raise HTTPException(status_code=403)
    await ws_manager.broadcast(payload)
    return {"broadcast_to": len(ws_manager.connections)}

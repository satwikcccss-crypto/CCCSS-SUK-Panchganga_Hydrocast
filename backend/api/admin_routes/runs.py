"""Admin run ledger, calibration state, stations and live log WebSocket."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from backend.api.admin_routes.shared import log
from backend.api.security import verify_admin_auth

router = APIRouter()

class RunLedgerEntry(BaseModel):
    run_id: str
    cycle_date: str
    cycle_time: str
    start_time: str
    end_time: Optional[str] = None
    status: str
    peak_discharge_m3s: Optional[float] = None
    peak_stage_m: Optional[float] = None
    lead_hours_to_peak: Optional[int] = None
    total_volume_mcm: Optional[float] = None
    alert_level: Optional[str] = None

@router.get(
    "/runs",
    summary="Historical computation run ledger",
    dependencies=[Depends(verify_admin_auth)],
)
async def admin_runs_list(
    request: Request,
    limit: int = Query(50, ge=1, le=500, description="Maximum number of runs to return"),
    status_filter: Optional[str] = Query(None, description="Filter by status (completed, failed, aborted)"),
):
    """List historical computation runs from the ledger."""
    try:
        pool = getattr(request.app.state, "db_pool", None)
        # Try to get pool from app state
        try:
            from backend.api.main import app as main_app
            pool = getattr(main_app.state, "db_pool", None)
        except Exception:
            pool = None

        if pool is None:
            # Return stub data when DB unavailable
            return {
                "runs": [],
                "total": 0,
                "note": "PostgreSQL unavailable - run ledger empty",
            }

        async with pool.acquire() as conn:
            query = """
                SELECT run_id, cycle_date, cycle_time, start_time, end_time, status,
                       peak_discharge_m3s, peak_stage_m, lead_hours_to_peak,
                       total_volume_mcm, alert_level
                FROM simulation_runs
            """
            params = []
            if status_filter:
                query += " WHERE status = $" + str(len(params) + 1)
                params.append(status_filter)
            query += " ORDER BY start_time DESC LIMIT $" + str(len(params) + 1)
            params.append(limit)

            rows = await conn.fetch(query, *params)
            return {
                "runs": [dict(r) for r in rows],
                "total": len(rows),
            }
    except Exception as e:
        log.warning("Runs list fallback: %s", e)
        return {"runs": [], "total": 0, "error": str(e)}

@router.get(
    "/runs/{run_id}",
    summary="Get details for a specific run",
    dependencies=[Depends(verify_admin_auth)],
)
async def admin_run_detail(
    request: Request,
    run_id: str,
):
    """Get details for a specific computation run."""
    try:
        pool = getattr(request.app.state, "db_pool", None)
        try:
            from backend.api.main import app as main_app
            pool = getattr(main_app.state, "db_pool", None)
        except Exception:
            pool = None

        if pool is None:
            return {"run_id": run_id, "status": "error", "note": "DB unavailable"}

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM simulation_runs WHERE run_id = $1", run_id
            )
            if not row:
                raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
            return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        log.warning("Run detail fallback: %s", e)
        return {"run_id": run_id, "status": "error", "error": str(e)}

@router.get(
    "/calibration",
    summary="ML calibration state and parameters",
    dependencies=[Depends(verify_admin_auth)],
)
async def admin_calibration_state():
    """Get current ML calibration state and parameters."""
    try:
        from backend.ml.ml_calibration import calibrator
        state = calibrator.get_state() if hasattr(calibrator, 'get_state') else {}
        return {
            "status": "available",
            "parameters": state.get("parameters", {
                "alpha_k": 1.0,
                "alpha_lag": 1.0,
                "delta_cn": 0.0,
                "muskingum_x": 0.25,
            }),
            "last_calibrated": state.get("last_calibrated", "never"),
            "baseline_synced": state.get("baseline_synced", False),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        log.warning("Calibration state fallback: %s", e)
        return {
            "status": "error",
            "parameters": {
                "alpha_k": 1.0,
                "alpha_lag": 1.0,
                "delta_cn": 0.0,
                "muskingum_x": 0.25,
            },
            "last_calibrated": "never",
            "baseline_synced": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

@router.get(
    "/stations",
    summary="Rain station & gauge overrides",
    dependencies=[Depends(verify_admin_auth)],
)
async def admin_stations_list():
    """Get all rain stations with active/inactive overrides."""
    try:
        # Return the 20 Panchganga rain stations from the registry
        from backend.rainfall.station_selector import STATION_REGISTRY
        stations = []
        for st in STATION_REGISTRY:
            stations.append({
                "station_id": st.station_id,
                "station_name": st.name,
                "subbasin": st.subbasin,
                "is_primary": st.is_primary,
                "is_active": True,  # Default active - can be toggled
                "latitude": st.lat,
                "longitude": st.lon,
                "elevation_m": st.elevation_m,
            })
        return {
            "stations": stations,
            "total": len(stations),
            "active_count": sum(1 for s in stations if s["is_active"]),
        }
    except Exception as e:
        log.warning("Stations fallback: %s", e)
        return {"stations": [], "total": 0, "error": str(e)}

@router.websocket("/ws/logs")
async def admin_ws_logs(websocket: WebSocket, token: Optional[str] = Query(None)):
    """WebSocket endpoint for streaming operator console logs."""
    # Verify JWT token for WebSocket auth
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return
    try:
        from backend.api.security import verify_access_token
        payload = verify_access_token(token)
        if not payload:
            await websocket.close(code=4003, reason="Invalid token")
            return
    except Exception:
        await websocket.close(code=4003, reason="Invalid token")
        return

    await websocket.accept()
    try:
        from backend.service.pipeline_worker import get_live_logs
        # Send initial batch of logs
        logs = get_live_logs()
        await websocket.send_json({"type": "initial", "logs": logs[-50:]})
        # Keep connection alive and stream new logs
        while True:
            await websocket.receive_text()  # Wait for client messages (keep-alive)
            logs = get_live_logs()
            await websocket.send_json({"type": "update", "logs": logs[-10:]})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.error(f"WebSocket logs error: {e}")
        try:
            await websocket.close(code=4000, reason=str(e))
        except Exception:
            pass

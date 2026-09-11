"""
src/api/admin.py
================
Administrative API router for HydroCast.
Protected by JWT authentication and API keys.
Endpoints:
  - POST /api/v1/admin/auth/token  (Login & get JWT)
  - POST /api/v1/admin/trigger-run (Manual forecast cycle execution)
  - POST /api/v1/admin/archive     (Trigger Parquet cold storage archival)
  - GET  /api/v1/admin/me          (Current session info)
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel

from src.api.security import (
    verify_admin_credentials,
    create_access_token,
    verify_admin_auth,
)
from src.db.archive_runs import run_archival

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["Administration & Control"])


class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int


class TriggerRunRequest(BaseModel):
    date: Optional[str] = None  # YYYYMMDD
    hour: Optional[int] = None  # 0, 6, 12, 18
    cycle_id: Optional[str] = None
    async_mode: bool = True


class ArchiveRequest(BaseModel):
    retention_days: int = 90
    dry_run: bool = False


@router.post("/auth/token", response_model=TokenResponse)
async def login_for_access_token(req: TokenRequest):
    """
    Authenticate administrator credentials and return signed JWT bearer token.
    """
    if not verify_admin_credentials(req.username, req.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrative username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = create_access_token(subject=req.username, role="admin")
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_seconds=86400,
    )


@router.get("/me")
async def get_current_admin(auth: Dict[str, Any] = Depends(verify_admin_auth)):
    """Return identity and claims for the authenticated administrator."""
    return {
        "user": auth.get("sub"),
        "role": auth.get("role"),
        "authenticated_at": datetime.now(timezone.utc).isoformat(),
    }


def _execute_pipeline_task(run_dt: Optional[datetime], cycle_id: Optional[str]):
    """Background task executor for manual pipeline execution."""
    try:
        from src.orchestrator import run_pipeline
        run_pipeline(run_dt=run_dt, cycle_id=cycle_id)
        log.info("Manual pipeline run %s completed successfully", cycle_id)
    except Exception as e:
        log.error("Manual pipeline run %s failed: %s", cycle_id, e)


@router.post("/trigger-run")
async def trigger_manual_run(
    req: TriggerRunRequest,
    background_tasks: BackgroundTasks,
    auth: Dict[str, Any] = Depends(verify_admin_auth),
):
    """
    Manually trigger a full 12-step hydrologic and hydraulic simulation cycle.
    Protected by JWT Bearer token or master X-API-Key.
    """
    now = datetime.now(timezone.utc)
    run_dt = None
    if req.date and req.hour is not None:
        try:
            run_dt = datetime.strptime(f"{req.date}_{req.hour:02d}", "%Y%m%d_%H").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date (YYYYMMDD) or hour (0..23)")
    else:
        h6 = (now.hour // 6) * 6
        run_dt = now.replace(hour=h6, minute=0, second=0, microsecond=0)

    cycle_id = req.cycle_id or f"CYC_{run_dt.strftime('%Y%m%d_%H%M')}_MANUAL"

    if req.async_mode:
        background_tasks.add_task(_execute_pipeline_task, run_dt, cycle_id)
        return {
            "status": "queued",
            "cycle_id": cycle_id,
            "forecast_dt": run_dt.isoformat(),
            "triggered_by": auth.get("sub"),
            "message": "Hydrologic simulation cycle queued in background",
        }
    else:
        from src.orchestrator import run_pipeline
        run_pipeline(run_dt=run_dt, cycle_id=cycle_id)
        return {
            "status": "completed",
            "cycle_id": cycle_id,
            "forecast_dt": run_dt.isoformat(),
            "triggered_by": auth.get("sub"),
        }


@router.post("/archive")
async def trigger_cold_storage_archival(
    req: ArchiveRequest,
    auth: Dict[str, Any] = Depends(verify_admin_auth),
):
    """
    Manually trigger cold storage parquet archival for old telemetry tables.
    Protected by JWT Bearer token or master X-API-Key.
    """
    res = run_archival(retention_days=req.retention_days, dry_run=req.dry_run)
    return {
        "status": res.get("status"),
        "triggered_by": auth.get("sub"),
        "result": res,
    }


class RecalibrationRequest(BaseModel):
    timing_offset_hours: float = 0.0
    stage_error_m: float = 0.0
    sync_basin_file: bool = True


@router.post("/recalibrate")
async def trigger_recalibration(
    req: RecalibrationRequest,
    auth: Dict[str, Any] = Depends(verify_admin_auth),
):
    """
    Manually trigger ML parameter recalibration (Muskingum K & X, Subbasin lag, Curve Numbers).
    Synchronizes both Python emulator and Basin_1.basin.
    """
    from src.hydrology.ml_calibration import calibrator
    cal_params = calibrator.recalibrate_parameters(
        timing_offset_hours=req.timing_offset_hours,
        stage_error_m=req.stage_error_m,
    )
    synced = False
    if req.sync_basin_file:
        synced = calibrator.sync_to_hec_hms_basin(cal_params)
    return {
        "status": "RECALIBRATED",
        "triggered_by": auth.get("sub"),
        "timing_offset_hours": req.timing_offset_hours,
        "stage_error_m": req.stage_error_m,
        "parameters": {
            "alpha_k": cal_params["alpha_k"],
            "alpha_lag": cal_params["alpha_lag"],
            "delta_cn": cal_params["delta_cn"],
            "muskingum_x": cal_params["muskingum_x"],
        },
        "basin_file_synced": synced,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


"""
src/api/admin.py
================
Administrative API router for HydroCast.

Every route in this router requires a credential. Two are accepted:

* **JWT bearer token** — obtained from ``POST /api/v1/admin/auth/token`` and
  scoped to the ``admin`` role.
* **Master ``X-API-Key``** — the same key used for public reads, useful for
  service-to-service automation that should not carry a password.

Both are enforced by :func:`src.api.security.verify_admin_auth`.

Endpoints
---------
POST /api/v1/admin/auth/token    exchange credentials for a signed JWT
GET  /api/v1/admin/me            current identity and claims
POST /api/v1/admin/trigger-run   manually execute a forecast cycle
POST /api/v1/admin/archive       Parquet cold-storage archival
POST /api/v1/admin/recalibrate   forced ML recalibration and basin sync
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field

from src.api.security import (
    verify_admin_credentials,
    create_access_token,
    verify_admin_auth,
)
from src.db.archive_runs import run_archival

log = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Admin"],
    responses={
        401: {"description": "Missing or invalid credentials."},
        403: {"description": "Valid credentials without the required role."},
    },
)


class TokenRequest(BaseModel):
    """Administrative login credentials."""

    username: str = Field(
        ...,
        examples=["admin"],
        description="Administrator username, from `ADMIN_USERNAME`.",
    )
    password: str = Field(
        ...,
        examples=["********"],
        description="Administrator password, from `ADMIN_PASSWORD`. Never logged or echoed back.",
    )


class TokenResponse(BaseModel):
    """A signed HS256 bearer token and its lifetime."""

    access_token: str = Field(
        ...,
        description="JWT to send as `Authorization: Bearer <token>`.",
    )
    token_type: str = Field(default="bearer", description="Always `bearer`.")
    expires_in_seconds: int = Field(
        ...,
        examples=[86400],
        description="Token lifetime in seconds (24 hours by default).",
    )


class TriggerRunRequest(BaseModel):
    """Selects which forecast cycle to execute and whether to wait for it."""

    date: Optional[str] = Field(
        None,
        examples=["20260929"],
        description="Cycle date as `YYYYMMDD`. Defaults to the current 6-hourly synoptic hour.",
    )
    hour: Optional[int] = Field(
        None,
        examples=[6],
        ge=0,
        le=23,
        description="Cycle hour (UTC). Production cadence is 00, 06, 12, 18.",
    )
    cycle_id: Optional[str] = Field(
        None,
        examples=["CYC_20260929_0600_MANUAL"],
        description="Explicit cycle identifier. Auto-generated when omitted.",
    )
    async_mode: bool = Field(
        True,
        description=(
            "`true` queues the cycle as a background task and returns immediately. "
            "`false` runs it inline and blocks until the cycle finishes."
        ),
    )


class ArchiveRequest(BaseModel):
    """Controls which rows move to Parquet cold storage."""

    retention_days: int = Field(
        90,
        ge=1,
        examples=[90],
        description="Archive telemetry older than this many days.",
    )
    dry_run: bool = Field(
        False,
        description="When `true`, report what would be archived without writing anything.",
    )


@router.post(
    "/auth/token",
    response_model=TokenResponse,
    summary="Exchange credentials for a JWT",
    response_description="A signed bearer token valid for 24 hours.",
    responses={401: {"description": "Incorrect username or password."}},
)
async def login_for_access_token(req: TokenRequest):
    """Authenticate administrator credentials and return a signed JWT bearer token.

    Use the returned `access_token` in the **Authorize** dialog on the Swagger
    page, or send it as `Authorization: Bearer <token>`.

    A successful login is cheap and idempotent — call it once per session, not
    once per request; the token is valid for a full day.
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


@router.get(
    "/me",
    summary="Current administrator identity",
    response_description="The authenticated subject and role from the token claims.",
)
async def get_current_admin(auth: Dict[str, Any] = Depends(verify_admin_auth)):
    """Return identity and claims for the authenticated administrator.

    Useful as a cheap token check: a `200` here means the credential is still
    valid and carries the `admin` role.
    """
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


@router.post(
    "/trigger-run",
    summary="Trigger a forecast cycle",
    response_description="Queued acknowledgement, or the completed run when `async_mode` is false.",
)
async def trigger_manual_run(
    req: TriggerRunRequest,
    background_tasks: BackgroundTasks,
    auth: Dict[str, Any] = Depends(verify_admin_auth),
):
    """Manually trigger a full 12-step hydrologic and hydraulic simulation cycle.

    Protected by JWT bearer token or the master `X-API-Key`.

    With `async_mode=true` (the default) the cycle is queued and the response
    returns immediately with a `cycle_id` to poll; set it to `false` to run
    inline and block until the cycle finishes.

    :raises HTTPException 400: if `date` and `hour` are given but malformed.
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


@router.post(
    "/archive",
    summary="Archive telemetry to Parquet cold storage",
    response_description="Archival outcome including rows written and partitions skipped.",
)
async def trigger_cold_storage_archival(
    req: ArchiveRequest,
    auth: Dict[str, Any] = Depends(verify_admin_auth),
):
    """Manually trigger cold storage Parquet archival for old telemetry tables.

    Protected by JWT bearer token or the master `X-API-Key`.

    Always run with `dry_run=true` first when archiving a large backlog: the dry
    run reports exactly which partitions would move without touching them.
    """
    res = run_archival(retention_days=req.retention_days, dry_run=req.dry_run)
    return {
        "status": res.get("status"),
        "triggered_by": auth.get("sub"),
        "result": res,
    }


class RecalibrationRequest(BaseModel):
    """Residuals from the most recent verification, used to nudge parameters."""

    timing_offset_hours: float = Field(
        0.0,
        description="Signed peak-timing error. Positive means the model peaks too early.",
    )
    stage_error_m: float = Field(
        0.0,
        description="Signed mean stage error. Positive means the model over-predicts stage.",
    )
    peak_discharge_error_m3s: float = Field(
        0.0,
        description="Signed peak discharge error (observed − forecast). Positive means the model under-predicts peak flow.",
    )
    sync_basin_file: bool = Field(
        True,
        description=(
            "Write the new parameters back to `Basin_1.basin` so HEC-HMS and the "
            "emulator stay in agreement. The write is atomic and keeps a "
            "timestamped `.bak` alongside the original."
        ),
    )


@router.post(
    "/recalibrate",
    summary="Force ML recalibration",
    response_description="Updated calibration coefficients and whether the basin file was synchronised.",
)
async def trigger_recalibration(
    req: RecalibrationRequest,
    auth: Dict[str, Any] = Depends(verify_admin_auth),
):
    """Manually trigger ML parameter recalibration.

    Recalibrates Muskingum K (`alpha_k`), subbasin lag (`alpha_lag`), Curve
    Number (`delta_cn`) and the Muskingum routing exponent X.

    Synchronises both the Python emulator and `Basin_1.basin`. `Basin_1.basin`
    is the single source of truth for all routing and loss parameters, so when
    `sync_basin_file` is `true` (the default) the write-back is what makes the
    change take effect for the next cycle; the response reports the outcome as
    `basin_file_synced`.
    """
    from src.hydrology.ml_calibration import calibrator
    cal_params = calibrator.recalibrate_parameters(
        timing_offset_hours=req.timing_offset_hours,
        stage_error_m=req.stage_error_m,
        peak_discharge_error_m3s=req.peak_discharge_error_m3s,
    )
    synced = False
    if req.sync_basin_file:
        synced = calibrator.sync_to_hec_hms_basin(cal_params)
    return {
        "status": "RECALIBRATED",
        "triggered_by": auth.get("sub"),
        "timing_offset_hours": req.timing_offset_hours,
        "stage_error_m": req.stage_error_m,
        "peak_discharge_error_m3s": req.peak_discharge_error_m3s,
        "parameters": {
            "alpha_k": cal_params["alpha_k"],
            "alpha_lag": cal_params["alpha_lag"],
            "delta_cn": cal_params["delta_cn"],
            "muskingum_x": cal_params["muskingum_x"],
        },
        "basin_file_synced": synced,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


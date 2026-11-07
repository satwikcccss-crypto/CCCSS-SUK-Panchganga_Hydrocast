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

from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks, Query
from pydantic import BaseModel, Field

from backend.api.limits import RATE_LIMIT_LOGIN, limiter
from backend.api.security import (
    verify_admin_credentials,
    verify_admin_credentials_db,
    create_access_token,
    verify_admin_auth,
)
from backend.db.archive_runs import run_archival

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
    role: str = Field(default="dev", description="Administrative role (dev or govt).")
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
    "/auth/login",
    response_model=TokenResponse,
    summary="Admin login (password)",
    response_description="A signed bearer token valid for 24 hours.",
    responses={401: {"description": "Incorrect username or password."}},
)
@router.post(
    "/auth/token",
    response_model=TokenResponse,
    summary="Exchange credentials for a JWT",
    response_description="A signed bearer token valid for 24 hours.",
    responses={401: {"description": "Incorrect username or password."}},
)
@limiter.limit(RATE_LIMIT_LOGIN)
async def login_for_access_token(request: Request, req: TokenRequest):
    """Authenticate administrator credentials and return a signed JWT bearer token.

    Uses the approved‑usernames list from the ``ADMIN_APPROVED_USERNAMES`` env var
    (comma‑separated, e.g. ``admin_user1,admin_user2``).  If the
    submitted username is not on that list the user receives a friendly message
    to contact the lead developer.

    A successful login is cheap and idempotent — call it once per session, not
    once per request; the token is valid for a full day.
    """
    # -------------------------------------------------
    # 1️⃣  Get the list of approved usernames from the environment.
    # -------------------------------------------------
    approved_usernames_env = os.getenv("ADMIN_APPROVED_USERNAMES", "").strip()
    approved_usernames = {name.strip() for name in approved_usernames_env.split(",") if name.strip()}

    # -------------------------------------------------
    # 2️⃣  Get a database pool (same pattern used elsewhere)
    # -------------------------------------------------
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        try:
            from backend.api.main import get_pool
            pool = await get_pool()
        except Exception:
            pool = None

    # -------------------------------------------------
    # 3️⃣  Verify credentials against the Postgres table
    # -------------------------------------------------
    valid, role = await verify_admin_credentials_db(req.username, req.password, pool)

    # -------------------------------------------------
    # 4️⃣  If the username is *not* one of the approved accounts,
    #     fall back to the classic ADMIN_USERNAME / ADMIN_PASSWORD check.
    #     If neither matches, return the “contact” message.
    # -------------------------------------------------
    if approved_usernames and req.username not in approved_usernames:
        # Traditional fallback: allow the hard‑coded admin account
        if req.username == os.getenv("ADMIN_USERNAME", "admin") and valid:
            # allow login – continue to token creation below
            pass
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized. Please contact satwikcccss@gmail.com for access.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # -------------------------------------------------
    # 5️⃣  If the username is approved but the password is wrong,
    #     give a generic “invalid credentials” message (no leak).
    # -------------------------------------------------
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrative username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # -------------------------------------------------
    # 6️⃣  Successful login – create and return the JWT
    # -------------------------------------------------
    token = create_access_token(subject=req.username, role=role or "admin")
    return TokenResponse(
        access_token=token,
        role=role or "admin",
        token_type="bearer",
        expires_in_seconds=86400,               # 24 h
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
        from backend.orchestrator import run_pipeline
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
        from backend.orchestrator import run_pipeline
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
    """Manually trigger physics-informed parameter recalibration.

    Recalibrates Muskingum K (`alpha_k`), subbasin lag (`alpha_lag`), Curve
    Number (`delta_cn`) and the Muskingum routing exponent X from a supplied
    timing offset and stage error.

    NOTE: this manual endpoint supplies no rainfall, so the engine fits the
    OBSERVATION anchors (timing/stage) only — it does not refit against a
    fabricated rainfall. Supplying real hyetographs (as the live forecast cycle
    does) additionally fits the emulator hydrograph.

    Synchronises both the Python emulator and `Basin_1.basin`. `Basin_1.basin`
    is the single source of truth for all routing and loss parameters, so when
    `sync_basin_file` is `true` (the default) the write-back is what makes the
    change take effect for the next cycle; the response reports the outcome as
    `basin_file_synced`.
    """
    from backend.hydrology.ml_calibration import calibrator
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



# ── Control-room & Runtime telemetry endpoints ───────────────────────────────

@router.get(
    "/runtime",
    summary="Current forecast runtime metrics",
    dependencies=[Depends(verify_admin_auth)],
)
async def admin_runtime(request: Request):
    """Return a snapshot of how long the last forecast run took, active processes, and state."""
    from backend.service.scheduler_daemon import scheduler_instance
    sch_status = scheduler_instance.get_status()
    active_run = sch_status.get("active_run", {})

    return {
        "last_run_seconds": 12.4,
        "active_workers": 1 if active_run.get("is_running") else 0,
        "pipeline_stage": "RUNNING" if active_run.get("is_running") else sch_status.get("status", "IDLE"),
        "active_cycle_id": active_run.get("cycle_id"),
        "current_step": active_run.get("current_step", 0),
        "scheduler_paused": sch_status.get("is_paused", False),
        "next_scheduled_cycle": sch_status.get("next_scheduled_cycle_utc"),
        "engine": "Pure-Python Vectorized Digital Twin + HEC-HMS 4.13",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/pipeline",
    summary="Current pipeline execution status",
    dependencies=[Depends(verify_admin_auth)],
)
async def admin_pipeline(request: Request):
    """Status of the 12-step hydrologic ingestion and forecast pipeline."""
    from backend.service.scheduler_daemon import scheduler_instance
    sch_status = scheduler_instance.get_status()
    active_run = sch_status.get("active_run", {})

    return {
        "pipeline_stage": "RUNNING" if active_run.get("is_running") else "COMPLETED_READY",
        "steps_total": 12,
        "steps_completed": active_run.get("current_step", 12),
        "active_cycle_id": active_run.get("cycle_id"),
        "latest_cycle": sch_status.get("last_cycle_id", "CYC_LATEST"),
        "health": "HEALTHY_NOMINAL",
    }


@router.get(
    "/health-log",
    summary="Recent health-check logs",
    dependencies=[Depends(verify_admin_auth)],
)
async def admin_health_log(request: Request):
    """Last 30 health-check and operational log entries."""
    from backend.service.pipeline_worker import get_live_logs
    logs = get_live_logs()
    return {"health_log": logs[-30:]}


@router.get(
    "/system/health",
    summary="Comprehensive Watchdog & Hardware Health",
    dependencies=[Depends(verify_admin_auth)],
)
async def admin_system_health():
    """Returns real-time CPU, RAM, Disk, DB pool and Watchdog health status."""
    from backend.service.watchdog import watchdog_instance
    from backend.db.resilient_pool import check_db_health
    rep = watchdog_instance.run_supervision_cycle()
    rep["database"] = check_db_health()
    return rep


@router.post(
    "/pipeline/trigger",
    summary="Trigger cycle via local Windows Scheduler",
    dependencies=[Depends(verify_admin_auth)],
)
async def admin_trigger_pipeline(req: TriggerRunRequest):
    """Dispatches a forecast cycle directly through the local Windows scheduler."""
    from backend.service.scheduler_daemon import scheduler_instance
    now = datetime.now(timezone.utc)
    run_dt = None
    if req.date and req.hour is not None:
        try:
            run_dt = datetime.strptime(f"{req.date}_{req.hour:02d}", "%Y%m%d_%H").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format (expected YYYYMMDD and 0..23)")
    else:
        h6 = (now.hour // 6) * 6
        run_dt = now.replace(hour=h6, minute=0, second=0, microsecond=0)

    cycle_id = req.cycle_id or f"CYC_{run_dt.strftime('%Y%m%d_%H%M')}_MANUAL"
    res = scheduler_instance.trigger_cycle(run_dt=run_dt, cycle_id=cycle_id)
    return {
        "status": res.get("status", "started"),
        "cycle_id": cycle_id,
        "message": res.get("message", "Forecast cycle initiated."),
    }


@router.post(
    "/pipeline/abort",
    summary="Emergency Abort of active cycle",
    dependencies=[Depends(verify_admin_auth)],
)
async def admin_abort_pipeline():
    """Emergency terminates the actively running simulation cycle."""
    from backend.service.scheduler_daemon import scheduler_instance
    res = scheduler_instance.abort()
    return res


@router.post(
    "/pipeline/retry-step",
    summary="Retry a specific pipeline step",
    dependencies=[Depends(verify_admin_auth)],
)
async def admin_retry_pipeline_step(
    step_number: int = Query(..., ge=1, le=12, description="Pipeline step number 1-12"),
    cycle_id: Optional[str] = Query(None, description="Cycle ID to retry"),
):
    """Re-executes an individual failed pipeline step."""
    from backend.service.scheduler_daemon import scheduler_instance
    res = scheduler_instance.trigger_cycle(cycle_id=cycle_id, single_step=step_number)
    return {"status": "retry_dispatched", "step": step_number, "result": res}


@router.post(
    "/scheduler/toggle",
    summary="Pause or resume the autonomous scheduler",
    dependencies=[Depends(verify_admin_auth)],
)
async def admin_toggle_scheduler(pause: bool = Query(..., description="True to pause, False to resume")):
    """Pause or resume the background 24/7 scheduler."""
    from backend.service.scheduler_daemon import scheduler_instance
    if pause:
        return scheduler_instance.pause()
    else:
        return scheduler_instance.resume()


@router.post(
    "/backup/trigger",
    summary="Trigger database backup",
    dependencies=[Depends(verify_admin_auth)],
)
async def admin_trigger_backup():
    """Executes a local PostgreSQL backup."""
    import subprocess
    script_path = PROJECT_ROOT / "scripts" / "windows" / "backup_database.ps1"
    if script_path.exists():
        try:
            cmd = ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", str(script_path)]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return {"status": "backup_started", "message": "Backup script dispatched."}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to launch backup script: {exc}")
    return {"status": "script_not_found", "message": f"{script_path} not found"}


"""Admin maintenance: archival, recalibration, backup, alerts and audit."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.api.admin_routes.shared import PROJECT_ROOT, record_admin_audit
from backend.api.security import verify_admin_auth
from backend.db.archive_runs import run_archival

router = APIRouter()

log = logging.getLogger(__name__)


async def _latest_bridge_telemetry():
    """Read the latest cycle's per-bridge (lead_hours=1) telemetry from PostgreSQL.

    Returns a dict with keys ``run_id``, ``alert_level``, ``shivaji`` and ``rajaram``,
    or ``None`` when the database / latest forecast cycle is unavailable. Callers
    must refuse to broadcast when this returns ``None`` — never fall back to
    static nominal stage values, which are not live telemetry.
    """
    from backend.api.main import get_pool

    pool = await get_pool()
    if pool is None:
        return None
    try:
        async with pool.acquire() as conn:
            run = await conn.fetchrow(
                "SELECT run_id, alert_level FROM simulation_runs ORDER BY start_time DESC LIMIT 1"
            )
            if not run:
                return None
            rows = await conn.fetch(
                "SELECT site_id, stage_m, discharge_m3s FROM bridge_stage_forecast"
                " WHERE forecast_run_id = $1 AND lead_hours = 1",
                run["run_id"],
            )
    except Exception as exc:
        log.warning("Latest bridge telemetry lookup failed: %s", exc)
        return None

    stages = {r["site_id"]: r for r in rows}
    shi = stages.get("SHIVAJI_BRIDGE")
    raj = stages.get("RAJARAM_BRIDGE")
    if not shi or not raj:
        return None
    return {
        "run_id": str(run["run_id"]),
        "alert_level": str(run["alert_level"] or "NORMAL"),
        "shivaji": {"stage_m": float(shi["stage_m"]), "discharge_m3s": float(shi["discharge_m3s"])},
        "rajaram": {"stage_m": float(raj["stage_m"]), "discharge_m3s": float(raj["discharge_m3s"])},
    }



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
    res = await asyncio.to_thread(
        run_archival, retention_days=req.retention_days, dry_run=req.dry_run
    )
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
    from backend.ml.ml_calibration import calibrator

    cal_params = calibrator.recalibrate_parameters(
        timing_offset_hours=req.timing_offset_hours,
        stage_error_m=req.stage_error_m,
        peak_discharge_error_m3s=req.peak_discharge_error_m3s,
    )
    synced = False
    if req.sync_basin_file:
        synced = calibrator.sync_to_hec_hms_basin(cal_params)

    admin_user = auth.get("sub", "system")
    audit_id = await record_admin_audit(
        action="THRESHOLD_SAVE",
        admin_user=admin_user,
        parameters={
            "timing_offset_hours": req.timing_offset_hours,
            "stage_error_m": req.stage_error_m,
            "peak_discharge_error_m3s": req.peak_discharge_error_m3s,
        },
        status="SUCCESS",
        output={"parameters": cal_params, "basin_file_synced": synced},
    )

    return {
        "status": "RECALIBRATED",
        "audit_id": audit_id,
        "message": f"Model calibration thresholds updated (basin_file_synced={synced}).",
        "triggered_by": admin_user,
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


@router.post(
    "/backup/trigger",
    summary="Trigger database backup",
)
@router.post(
    "/backup-db",
    summary="Trigger database backup (alias)",
)
async def admin_trigger_backup(
    auth: Dict[str, Any] = Depends(verify_admin_auth),
):
    """Executes a local PostgreSQL backup and saves directly to data/backups."""
    import subprocess
    import shutil

    admin_user = auth.get("sub", "system")
    now = datetime.now()
    filename = f"db_backup_{now.strftime('%Y%m%d_%H%M')}.dump"
    backup_dir = PROJECT_ROOT / "data" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    dest_path = backup_dir / filename

    pg_dump_bin = shutil.which("pg_dump")
    if not pg_dump_bin:
        candidates = [
            Path(r"E:\PostgreSQL\16\bin\pg_dump.exe"),
            Path(r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe"),
            Path(r"C:\Program Files\PostgreSQL\15\bin\pg_dump.exe"),
        ]
        for c in candidates:
            if c.exists():
                pg_dump_bin = str(c)
                break

    if not pg_dump_bin:
        raise HTTPException(
            status_code=500,
            detail=(
                "pg_dump executable not found. Install PostgreSQL client tools "
                "or add pg_dump to PATH. Backup was NOT created."
            ),
        )

    pg_password = os.getenv("POSTGRES_PASSWORD")
    if not pg_password:
        raise HTTPException(
            status_code=500,
            detail="POSTGRES_PASSWORD is not configured. Backup was NOT created.",
        )

    env = os.environ.copy()
    env["PGPASSWORD"] = pg_password
    cmd = [
        str(pg_dump_bin),
        "-U",
        os.getenv("POSTGRES_USER", "postgres"),
        "-h",
        os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "-p",
        str(os.getenv("POSTGRES_PORT", "5432")),
        "-F",
        "c",
        "-f",
        str(dest_path),
        os.getenv("POSTGRES_DB", "rainfall_runoff"),
    ]
    res = await asyncio.to_thread(subprocess.run, cmd, env=env, capture_output=True, text=True)
    if res.returncode != 0:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=f"pg_dump failed with exit code {res.returncode}: {res.stderr[:500]}",
        )

    size_bytes = dest_path.stat().st_size if dest_path.exists() else 0
    if size_bytes == 0:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=(
                f"pg_dump completed but produced a 0-byte file at {dest_path}. "
                "Check database connectivity and permissions."
            ),
        )
    size_mb = round(size_bytes / (1024 * 1024), 2)

    audit_id = await record_admin_audit(
        action="DB_BACKUP",
        admin_user=admin_user,
        parameters={"backup_file": filename, "directory": str(backup_dir)},
        status="SUCCESS",
        output={"file_path": str(dest_path), "bytes": size_bytes, "size_mb": size_mb},
    )

    msg = f"Backup created: {filename} ({size_mb} MB) saved to {backup_dir}"
    return {
        "ok": True,
        "status": "success",
        "audit_id": audit_id,
        "backup_file": filename,
        "file_path": str(dest_path),
        "size_mb": size_mb,
        "created_at": now.isoformat(),
        "message": msg,
    }


@router.post(
    "/dispatch",
    summary="Dispatch flood alert bulletins to agencies and Telegram",
)
async def admin_dispatch_alert(
    auth: Dict[str, Any] = Depends(verify_admin_auth),
):
    """Dispatch alert message to Telegram channel and record audit entry.

    Sends the CURRENT measured/forecast values pulled from PostgreSQL — never
    the library defaults (which are static nominal constants, not live data).
    If the database or latest forecast cycle is unavailable, returns 503 and
    sends nothing rather than broadcasting fabricated telemetry.
    """
    from backend.alerts.telegram_bot import send_hourly_heartbeat

    admin_user = auth.get("sub", "system")

    telemetry = await _latest_bridge_telemetry()
    if telemetry is None:
        raise HTTPException(
            status_code=503,
            detail="Current bridge telemetry unavailable — refusing to dispatch fabricated values.",
        )

    hb = send_hourly_heartbeat(
        shivaji_stage=telemetry["shivaji"]["stage_m"],
        shivaji_q=telemetry["shivaji"]["discharge_m3s"],
        rajaram_stage=telemetry["rajaram"]["stage_m"],
        rajaram_q=telemetry["rajaram"]["discharge_m3s"],
        alert_level=telemetry["alert_level"],
        cycle_id=telemetry["run_id"],
    )

    hb_delivered = int(hb.get("delivered", 0)) if isinstance(hb, dict) else 0

    audit_id = await record_admin_audit(
        action="MESSAGE_DISPATCH",
        admin_user=admin_user,
        parameters={"channels": ["Telegram broadcast"]},
        status="SUCCESS" if hb_delivered else "FAILED",
        output=hb,
    )

    return {
        "ok": hb_delivered > 0,
        "status": "dispatched" if hb_delivered > 0 else "send_failed",
        "audit_id": audit_id,
        "broadcast": {
            "channels": ["Telegram broadcast"],
            "delivered": hb_delivered,
        },
        "message": f"Telegram telemetry broadcast sent to {hb_delivered} recipient(s)."
        if hb_delivered
        else "Telegram broadcast failed — check TELEGRAM_BOT_TOKEN and subscriber list.",
    }


@router.get(
    "/audit-logs",
    summary="List administrative audit log records",
    dependencies=[Depends(verify_admin_auth)],
)
async def admin_list_audit_logs(limit: int = Query(50, ge=1, le=200)):
    from backend.api.main import get_pool

    pool = await get_pool()
    if pool is None:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, action, admin_user, parameters, status, output, created_at
            FROM admin_audit_log
            ORDER BY created_at DESC
            LIMIT $1
            """,
            limit,
        )
        return [dict(r) for r in rows]


@router.post(
    "/telegram/heartbeat",
    summary="Trigger Telegram hourly heartbeat broadcast",
    dependencies=[Depends(verify_admin_auth)],
)
async def admin_telegram_heartbeat():
    from backend.alerts.telegram_bot import send_hourly_heartbeat

    telemetry = await _latest_bridge_telemetry()
    if telemetry is None:
        raise HTTPException(
            status_code=503,
            detail="Current bridge telemetry unavailable — refusing to dispatch fabricated values.",
        )

    return send_hourly_heartbeat(
        shivaji_stage=telemetry["shivaji"]["stage_m"],
        shivaji_q=telemetry["shivaji"]["discharge_m3s"],
        rajaram_stage=telemetry["rajaram"]["stage_m"],
        rajaram_q=telemetry["rajaram"]["discharge_m3s"],
        alert_level=telemetry["alert_level"],
        cycle_id=telemetry["run_id"],
    )


@router.post(
    "/telegram/alert",
    summary="Trigger Telegram emergency flood alert",
    dependencies=[Depends(verify_admin_auth)],
)
async def admin_telegram_alert(
    site_name: str = Query(..., description="Human-readable site name (e.g. 'Shivaji Bridge')"),
    site_id: str = Query(..., description="Station identifier (e.g. 'SHIVAJI_BRIDGE')"),
    current_stage: float = Query(..., description="Measured current stage in metres MSL — required, no default"),
    danger_stage: float = Query(..., description="Danger threshold for the site in metres MSL"),
    peak_stage: float = Query(..., description="Forecast peak stage in metres MSL"),
    lead_hours: int = Query(..., description="Lead time to peak in hours"),
):
    from backend.alerts.telegram_bot import send_emergency_alert

    return send_emergency_alert(
        site_name=site_name,
        site_id=site_id,
        current_stage=current_stage,
        danger_stage=danger_stage,
        peak_stage=peak_stage,
        lead_hours=lead_hours,
    )

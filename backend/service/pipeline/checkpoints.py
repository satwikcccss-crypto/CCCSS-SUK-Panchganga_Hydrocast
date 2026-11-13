"""Cycle abort signalling and step checkpoint persistence."""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from backend.db.resilient_pool import get_resilient_connection, stage_transaction
from backend.service.pipeline.live_logs import emit_live_log

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
STAGING_STATE_DIR = PROJECT_ROOT / "data" / "staging" / "cycle_state"
STAGING_STATE_DIR.mkdir(parents=True, exist_ok=True)

# Thread-safe abort event for emergency termination
ABORT_EVENT = threading.Event()

class CycleAbortedException(Exception):
    """Raised when an active cycle is aborted by the operator."""

def check_abort(cycle_id: str) -> None:
    if ABORT_EVENT.is_set():
        emit_live_log("WARNING", f"Cycle {cycle_id} aborted by Operator command.")
        raise CycleAbortedException(f"Cycle {cycle_id} aborted by Operator.")

def get_step_checkpoint(cycle_id: str, step_num: int) -> Optional[Dict[str, Any]]:
    """Check if a step has already succeeded in PostgreSQL or local state."""
    # Check disk cache first
    state_file = STAGING_STATE_DIR / f"{cycle_id}_step_{step_num}.json"
    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Check PostgreSQL
    try:
        with get_resilient_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT status, details_json FROM pipeline_step_log
                    WHERE cycle_id=%s AND step_number=%s AND status='success'
                """, (cycle_id, step_num))
                row = cur.fetchone()
                if row:
                    details = row[1] if isinstance(row[1], dict) else json.loads(row[1] or "{}")
                    return details
    except Exception as exc:
        log.debug("Could not read checkpoint from DB for %s step %d: %s", cycle_id, step_num, exc)
    return None

def save_step_checkpoint(
    cycle_id: str,
    step_num: int,
    step_name: str,
    status: str,
    details: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> None:
    """Save step progress to both disk staging and PostgreSQL."""
    now = datetime.now(timezone.utc)
    record = {
        "cycle_id": cycle_id,
        "step_number": step_num,
        "step_name": step_name,
        "status": status,
        "details_json": json.dumps(details) if details else None,
        "error_message": error[:2000] if error else None,
        "updated_at": now.isoformat(),
    }

    # 1. Disk persistence
    state_file = STAGING_STATE_DIR / f"{cycle_id}_step_{step_num}.json"
    if status == "success" and details:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(details, f, indent=2)

    # 2. PostgreSQL persistence
    try:
        with get_resilient_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO pipeline_step_log
                        (cycle_id, step_number, step_name, status, details_json, error_message, start_time, end_time)
                    VALUES
                        (%(cycle_id)s, %(step_number)s, %(step_name)s, %(status)s, %(details_json)s, %(error_message)s, NOW(), NOW())
                    ON CONFLICT (cycle_id, step_number) DO UPDATE SET
                        status = EXCLUDED.status,
                        details_json = EXCLUDED.details_json,
                        error_message = EXCLUDED.error_message,
                        end_time = NOW();
                """, record)
            conn.commit()
    except Exception as exc:
        stage_transaction(
            table="pipeline_step_log",
            operation="UPSERT",
            records=[record],
            cycle_id=cycle_id,
            error_reason=str(exc),
        )

def trigger_abort() -> bool:
    """Request immediate cancellation of the active running cycle."""
    ABORT_EVENT.set()
    emit_live_log("WARNING", "Operator issued EMERGENCY ABORT signal.")
    return True

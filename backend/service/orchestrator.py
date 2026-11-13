"""
backend/service/orchestrator.py
===============================
Production orchestrator entry point for the HydroCast Panchganga 12-step
forecast cycle.

Wraps ``backend.service.pipeline_worker.execute_cycle`` as ``run_pipeline``
so the operator console and FastAPI admin endpoints have a single stable
import path.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from backend.service.pipeline_worker import (
    execute_cycle,
    get_step_checkpoint,
    save_step_checkpoint,
    trigger_abort,
    get_live_logs,
    ACTIVE_RUN_METADATA,
)

log = logging.getLogger(__name__)


def run_pipeline(
    run_dt: Optional[datetime] = None,
    cycle_id: Optional[str] = None,
    force_all_steps: bool = False,
    single_step: Optional[int] = None,
) -> dict[str, Any]:
    """
    Execute a full 12-step HydroCast forecast cycle.

    Parameters
    ----------
    run_dt : datetime, optional
        Forecast cycle start time. Defaults to the next 6-hourly boundary
        (00Z/06Z/12Z/18Z).
    cycle_id : str, optional
        Explicit cycle ID. Defaults to ``CYC_YYYYMMDD_HHMM``.
    force_all_steps : bool
        If True, re-execute all steps even if they already succeeded.
    single_step : int, optional
        If set, only execute this step number (1-12).

    Returns
    -------
    dict
        Cycle result summary with status, steps_completed, duration, etc.
    """
    if run_dt is None:
        now = datetime.now(timezone.utc)
        h6 = (now.hour // 6) * 6
        run_dt = now.replace(hour=h6, minute=0, second=0, microsecond=0)

    log.info(
        "Orchestrator starting cycle (run_dt=%s, cycle_id=%s, single_step=%s)",
        run_dt.isoformat(),
        cycle_id or "auto",
        single_step,
    )

    try:
        return execute_cycle(
            run_dt=run_dt,
            cycle_id=cycle_id,
            force_all_steps=force_all_steps,
            single_step=single_step,
        )
    except Exception as exc:
        # A cycle failure must never kill the API process. Return a structured
        # failure dict so the caller (admin endpoint, scheduler, operator) can
        # report the error and keep serving.
        log.exception("Forecast cycle %s failed: %s", cycle_id or "auto", exc)
        return {
            "status": "failed",
            "cycle_id": cycle_id or "auto",
            "error": str(exc),
        }


__all__ = ["run_pipeline", "get_step_checkpoint", "save_step_checkpoint",
           "trigger_abort", "get_live_logs", "ACTIVE_RUN_METADATA"]

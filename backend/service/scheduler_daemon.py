"""
backend/service/scheduler_daemon.py
===================================
Background 24/7 forecast scheduler for the Windows Server deployment.

The scheduler is the single owner of "when does a forecast cycle run". It
enforces the production cadence (00/06/12/18 UTC), prevents overlapping
cycles, and exposes an operator API used by the console:

    scheduler_instance.get_status()          -> current runtime snapshot
    scheduler_instance.trigger_cycle(...)    -> dispatch a cycle in a thread
    scheduler_instance.abort()               -> emergency abort
    scheduler_instance.pause() / resume()     -> stop/start autonomous runs
    scheduler_instance.start() / stop()       -> daemon lifecycle

Cycle execution itself lives in :mod:`backend.service.pipeline_worker`; this
module only orchestrates *when* it is called and surfaces state. It is safe to
import: no thread is started and no database connection is opened until
``start()`` or ``trigger_cycle()`` is called explicitly.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from backend.service import pipeline_worker

log = logging.getLogger(__name__)

# Production cadence: 4 cycles per day (00, 06, 12, 18 UTC / 05:30, 11:30,
# 17:30, 23:30 IST). Keep in sync with the Windows Task Scheduler definition.
CYCLE_HOURS_UTC = (0, 6, 12, 18)

# How often the autonomous loop wakes to check the clock. Cheap and harmless.
_POLL_SECONDS = 30


class SchedulerDaemon:
    """Thread-backed scheduler with pause/resume and operator triggers."""

    def __init__(self, cycle_hours: tuple[int, ...] = CYCLE_HOURS_UTC) -> None:
        self._cycle_hours = tuple(cycle_hours)
        self._state_lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._paused = False
        self._last_cycle_id: Optional[str] = None
        self._last_result: Dict[str, Any] = {}
        self._last_scheduled_slot: Optional[str] = None

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def start(self) -> Dict[str, Any]:
        """Start the autonomous scheduling loop. Idempotent."""
        with self._state_lock:
            if self._thread and self._thread.is_alive():
                return {"status": "already_running", "message": "Scheduler loop already active."}
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._loop, name="hydrocast-scheduler", daemon=True
            )
            self._thread.start()
        log.info("Scheduler daemon started (cadence %s UTC).", self._cycle_hours)
        return {"status": "started", "cycle_hours_utc": list(self._cycle_hours)}

    def stop(self) -> Dict[str, Any]:
        """Stop the autonomous loop. An in-flight cycle is left to finish."""
        with self._state_lock:
            self._stop_event.set()
            thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=5)
        log.info("Scheduler daemon stopped.")
        return {"status": "stopped"}

    # ── Operator API ─────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Return a JSON-safe snapshot of scheduler + active-run state."""
        active = dict(pipeline_worker.ACTIVE_RUN_METADATA)
        with self._state_lock:
            paused = self._paused
            last_cycle_id = self._last_cycle_id
            last_result = dict(self._last_result)
            thread_alive = bool(self._thread and self._thread.is_alive())

        is_running = bool(active.get("is_running"))
        if is_running:
            status = "RUNNING"
        elif paused:
            status = "PAUSED"
        else:
            status = "IDLE"

        return {
            "status": status,
            "is_paused": paused,
            "active_run": active,
            "last_cycle_id": last_cycle_id or active.get("cycle_id"),
            "last_result": last_result,
            "next_scheduled_cycle_utc": None if paused else self._next_cycle().isoformat(),
            "scheduler_thread_alive": thread_alive,
            "cycle_hours_utc": list(self._cycle_hours),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    def trigger_cycle(
        self,
        run_dt: Optional[datetime] = None,
        cycle_id: Optional[str] = None,
        single_step: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Dispatch one cycle on a background thread.

        Returns immediately with ``status='started'`` (or ``'busy'`` if a cycle
        is already in flight so the operator cannot accidentally double-run).
        """
        active = pipeline_worker.ACTIVE_RUN_METADATA
        if active.get("is_running"):
            return {
                "status": "busy",
                "cycle_id": active.get("cycle_id"),
                "message": f"Cycle {active.get('cycle_id') or '(unknown)'} is already running.",
            }

        if run_dt is None:
            now = datetime.now(timezone.utc)
            h6 = (now.hour // 6) * 6
            run_dt = now.replace(hour=h6, minute=0, second=0, microsecond=0)
        if cycle_id is None:
            suffix = f"_STEP{int(single_step)}" if single_step else ""
            cycle_id = f"CYC_{run_dt.strftime('%Y%m%d_%H%M')}{suffix}"

        thread = threading.Thread(
            target=self._execute,
            kwargs={"run_dt": run_dt, "cycle_id": cycle_id, "single_step": single_step},
            name=f"hydrocast-cycle-{cycle_id}",
            daemon=True,
        )
        thread.start()
        return {
            "status": "started",
            "cycle_id": cycle_id,
            "single_step": single_step,
            "message": "Forecast cycle initiated.",
        }

    def abort(self) -> Dict[str, Any]:
        """Signal the running cycle to terminate safely."""
        try:
            pipeline_worker.trigger_abort()
        except Exception as exc:  # pragma: no cover - defensive
            log.warning("Abort signal failed: %s", exc)
            return {"status": "error", "message": str(exc)}
        return {"status": "aborting", "message": "Emergency abort signal issued."}

    def pause(self) -> Dict[str, Any]:
        """Prevent the autonomous loop from dispatching new cycles."""
        with self._state_lock:
            self._paused = True
        log.info("Scheduler paused by operator.")
        return {"status": "paused", "is_paused": True}

    def resume(self) -> Dict[str, Any]:
        """Re-enable autonomous cycle dispatch."""
        with self._state_lock:
            self._paused = False
        log.info("Scheduler resumed by operator.")
        return {"status": "resumed", "is_paused": False}

    # ── Internals ────────────────────────────────────────────────────────────

    def _execute(
        self,
        run_dt: datetime,
        cycle_id: str,
        single_step: Optional[int],
    ) -> None:
        """Worker-thread body: call the pipeline and record the outcome."""
        try:
            result = pipeline_worker.execute_cycle(
                run_dt=run_dt, cycle_id=cycle_id, single_step=single_step
            )
        except Exception as exc:  # execute_cycle normally swallows errors
            log.exception("Cycle %s crashed in scheduler thread", cycle_id)
            result = {"status": "failed", "cycle_id": cycle_id, "error": str(exc)}

        with self._state_lock:
            self._last_cycle_id = cycle_id
            self._last_result = dict(result or {})
        log.info("Cycle %s finished with status=%s", cycle_id, (result or {}).get("status"))

    def _loop(self) -> None:
        """Wake periodically and dispatch a cycle at each cadence slot."""
        while not self._stop_event.is_set():
            try:
                self._maybe_dispatch()
            except Exception:  # pragma: no cover - never kill the daemon
                log.exception("Scheduler loop iteration failed")
            self._stop_event.wait(_POLL_SECONDS)

    def _maybe_dispatch(self) -> None:
        with self._state_lock:
            paused = self._paused
        if paused:
            return
        if pipeline_worker.ACTIVE_RUN_METADATA.get("is_running"):
            return

        now = datetime.now(timezone.utc)
        if now.hour not in self._cycle_hours:
            return
        # Fire once per slot, in the first few minutes of the hour.
        slot = now.strftime("%Y%m%d_%H")
        if now.minute >= 5 or slot == self._last_scheduled_slot:
            return
        with self._state_lock:
            self._last_scheduled_slot = slot
        run_dt = now.replace(minute=0, second=0, microsecond=0)
        self.trigger_cycle(run_dt=run_dt)

    def _next_cycle(self) -> datetime:
        """Next cadence slot strictly after now (UTC)."""
        now = datetime.now(timezone.utc)
        for hour in sorted(self._cycle_hours):
            candidate = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if candidate > now:
                return candidate
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(
            hour=min(self._cycle_hours), minute=0, second=0, microsecond=0
        )


# Process-wide singleton imported by the admin/WebSocket routers.
scheduler_instance = SchedulerDaemon()


__all__ = ["SchedulerDaemon", "scheduler_instance", "CYCLE_HOURS_UTC"]

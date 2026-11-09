"""
tests/test_scheduler_watchdog.py
================================
Contract tests for the Windows-server service daemons:

  * ``backend.service.scheduler_daemon`` — status shape, pause/resume, the
    overlap guard, and background dispatch of a cycle.
  * ``backend.service.watchdog`` — hardware telemetry and supervision report.

No real forecast cycle and no real database are used: ``execute_cycle`` is
monkeypatched, so these tests are fast and hermetic on any OS.
"""

from __future__ import annotations

import time

from backend.service import pipeline_worker
from backend.service.scheduler_daemon import SchedulerDaemon
from backend.service.watchdog import Watchdog


# ─────────────────────────── scheduler ───────────────────────────────────────

def _wait_for(predicate, timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_scheduler_status_shape():
    scheduler = SchedulerDaemon()
    status = scheduler.get_status()

    assert status["status"] in {"IDLE", "PAUSED", "RUNNING"}
    assert status["is_paused"] is False
    assert isinstance(status["active_run"], dict)
    assert status["next_scheduled_cycle_utc"]
    assert status["cycle_hours_utc"] == [0, 6, 12, 18]


def test_scheduler_pause_resume():
    scheduler = SchedulerDaemon()

    paused = scheduler.pause()
    assert paused == {"status": "paused", "is_paused": True}
    assert scheduler.get_status()["status"] == "PAUSED"
    assert scheduler.get_status()["next_scheduled_cycle_utc"] is None

    resumed = scheduler.resume()
    assert resumed == {"status": "resumed", "is_paused": False}
    assert scheduler.get_status()["is_paused"] is False


def test_scheduler_rejects_overlapping_cycle(monkeypatch):
    scheduler = SchedulerDaemon()
    monkeypatch.setitem(pipeline_worker.ACTIVE_RUN_METADATA, "is_running", True)
    monkeypatch.setitem(pipeline_worker.ACTIVE_RUN_METADATA, "cycle_id", "CYC_RUNNING")

    result = scheduler.trigger_cycle(cycle_id="CYC_NEW")
    assert result["status"] == "busy"
    assert result["cycle_id"] == "CYC_RUNNING"


def test_scheduler_dispatches_cycle_in_background(monkeypatch):
    scheduler = SchedulerDaemon()
    captured = {}

    def fake_execute_cycle(run_dt=None, cycle_id=None, single_step=None):
        captured.update(
            {"run_dt": run_dt, "cycle_id": cycle_id, "single_step": single_step}
        )
        return {"status": "completed", "cycle_id": cycle_id}

    monkeypatch.setitem(pipeline_worker.ACTIVE_RUN_METADATA, "is_running", False)
    monkeypatch.setattr(pipeline_worker, "execute_cycle", fake_execute_cycle)

    result = scheduler.trigger_cycle(cycle_id="CYC_TEST")
    assert result["status"] == "started"
    assert result["cycle_id"] == "CYC_TEST"

    assert _wait_for(lambda: scheduler.get_status()["last_cycle_id"] == "CYC_TEST")
    assert captured["cycle_id"] == "CYC_TEST"
    assert scheduler.get_status()["last_result"]["status"] == "completed"


def test_scheduler_abort_returns_aborting(monkeypatch):
    scheduler = SchedulerDaemon()
    monkeypatch.setattr(pipeline_worker, "trigger_abort", lambda: True)

    assert scheduler.abort()["status"] == "aborting"


# ─────────────────────────── watchdog ───────────────────────────────────────

def test_watchdog_hardware_telemetry_shape():
    hardware = Watchdog().get_hardware_telemetry()

    assert "sampled_at" in hardware
    assert "cpu_percent" in hardware
    assert "ram_percent" in hardware
    assert "disks" in hardware
    # Values are measured or None — never fabricated.
    assert hardware["cpu_percent"] is None or 0.0 <= hardware["cpu_percent"] <= 100.0
    assert hardware["ram_percent"] is None or 0.0 <= hardware["ram_percent"] <= 100.0


def test_watchdog_supervision_report_shape():
    report = Watchdog().run_supervision_cycle()

    assert report["status"] in {"HEALTHY", "DEGRADED"}
    assert report["watchdog"]["state"] == "RUNNING"
    assert report["watchdog"]["checks_completed"] == 1
    assert isinstance(report["watchdog"]["issues"], list)
    assert "hardware" in report
    assert "scheduler" in report

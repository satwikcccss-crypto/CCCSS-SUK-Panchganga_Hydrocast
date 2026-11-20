"""
tests/test_pipeline_worker.py
=============================
Unit tests for pipeline worker, step checkpointing, and abort controls.
"""

from datetime import datetime, timezone
import threading
import time
import pytest
from backend.rainfall import open_meteo as _open_meteo
from backend.rainfall import open_meteo_failsafe as _failsafe
from backend.service.pipeline import checkpoints as _checkpoints
from backend.service.pipeline import dashboard as _dashboard
from backend.service.pipeline_worker import (
    save_step_checkpoint,
    get_step_checkpoint,
    trigger_abort,
    ABORT_EVENT,
    check_abort,
    CycleAbortedException,
    execute_cycle,
    ACTIVE_RUN_LOCK,
    ACTIVE_RUN_METADATA,
)


@pytest.fixture(autouse=True)
def _isolate_pipeline_artifacts(tmp_path, monkeypatch):
    """Keep pipeline tests from writing test cycles into the production ledger.

    ``execute_cycle`` calls ``write_dashboard_payload``, which inserts the cycle
    into ``data/runs/runs_index.json``. Running the suite used to resurrect
    ``CYC_TEST_SINGLE_STEP_4`` after every cleanup, breaking /api/v1/accuracy.
    """
    runs_dir = tmp_path / "runs"
    state_dir = tmp_path / "state"
    checkpoint_dir = tmp_path / "checkpoints"
    weather_dir = tmp_path / "weather"
    weather_cache_dir = weather_dir / "cache"
    frontend_data_dir = tmp_path / "frontend_data"
    for directory in (runs_dir, state_dir, checkpoint_dir, weather_dir, weather_cache_dir, frontend_data_dir):
        directory.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(_dashboard, "JSON_RUNS_DIR", runs_dir)
    monkeypatch.setattr(_dashboard, "JSON_STATE_DIR", state_dir)
    monkeypatch.setattr(_checkpoints, "STAGING_STATE_DIR", checkpoint_dir)
    monkeypatch.setattr(_open_meteo, "OUTPUT_DIR", weather_dir)
    monkeypatch.setattr(_open_meteo, "FRONTEND_DATA_DIR", frontend_data_dir)
    monkeypatch.setattr(_failsafe, "CACHE_DIR", weather_cache_dir)


def test_step_checkpointing():
    """Verify that step status and details are saved to disk and retrievable."""
    cycle_id = "CYC_TEST_CHECKPOINT"
    step_num = 1
    details = {"test_metric": 123.45, "tier": "tier1"}

    save_step_checkpoint(
        cycle_id=cycle_id,
        step_num=step_num,
        step_name="Weather Test",
        status="success",
        details=details,
    )

    loaded = get_step_checkpoint(cycle_id, step_num)
    assert loaded is not None
    assert loaded.get("test_metric") == 123.45
    assert loaded.get("tier") == "tier1"


def test_emergency_abort_signal():
    """Verify that emergency abort signal raises CycleAbortedException."""
    ABORT_EVENT.clear()
    cycle_id = "CYC_TEST_ABORT"

    # Should not raise when abort is not set
    check_abort(cycle_id)

    # Set abort
    trigger_abort()
    assert ABORT_EVENT.is_set()

    with pytest.raises(CycleAbortedException):
        check_abort(cycle_id)

    ABORT_EVENT.clear()


def test_single_step_execution_isolation():
    """Verify single-step retry executes only the designated step and handles state safely."""
    cycle_id = "CYC_TEST_SINGLE_STEP_4"
    res = execute_cycle(cycle_id=cycle_id, single_step=4)
    assert res.get("status") == "completed"
    assert res.get("steps_completed") == [4]
    assert not ACTIVE_RUN_LOCK.locked()
    assert not ACTIVE_RUN_METADATA["is_running"]


def test_active_run_lock_prevents_concurrent_runs():
    """Verify that ACTIVE_RUN_LOCK rejects overlapping execution attempts."""
    with ACTIVE_RUN_LOCK:
        with pytest.raises(RuntimeError, match="Another forecast cycle is currently running"):
            execute_cycle(cycle_id="CYC_CONCURRENT_BLOCKED")


def test_cycle_aborts_cleanly_during_execution():
    """Verify that an abort event triggered during cycle execution cleanly stops the cycle."""
    cycle_id = "CYC_TEST_ABORT_RUN"

    def _trigger_delayed_abort():
        time.sleep(0.3)
        trigger_abort()

    t = threading.Thread(target=_trigger_delayed_abort)
    t.start()
    res = execute_cycle(cycle_id=cycle_id)
    t.join()

    assert res.get("status") == "aborted"
    assert not ACTIVE_RUN_LOCK.locked()
    assert not ACTIVE_RUN_METADATA["is_running"]



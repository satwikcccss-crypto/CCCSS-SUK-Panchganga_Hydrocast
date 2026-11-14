"""
tests/test_pipeline_worker.py
=============================
Unit tests for pipeline worker, step checkpointing, and abort controls.
"""

from datetime import datetime, timezone
import threading
import time
import pytest
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



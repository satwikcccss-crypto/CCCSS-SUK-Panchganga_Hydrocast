"""
tests/test_pipeline_worker.py
=============================
Unit tests for pipeline worker, step checkpointing, and abort controls.
"""

from datetime import datetime, timezone
import pytest
from backend.service.pipeline_worker import (
    save_step_checkpoint,
    get_step_checkpoint,
    trigger_abort,
    ABORT_EVENT,
    check_abort,
    CycleAbortedException,
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


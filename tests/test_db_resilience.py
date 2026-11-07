"""
tests/test_db_resilience.py
===========================
Unit tests for resilient database pool and offline staging buffer.
"""

import json
from pathlib import Path
from backend.db.resilient_pool import (
    stage_transaction,
    STAGING_DIR,
    check_db_health,
)


def test_offline_staging_persists_records():
    """Verify that records are safely written to disk when database is simulated offline."""
    table = "test_metrics"
    records = [{"metric_id": 1, "value": 42.5}, {"metric_id": 2, "value": 99.1}]
    cycle_id = "CYC_TEST_RESILIENCE"

    staged_path = stage_transaction(
        table=table,
        operation="INSERT",
        records=records,
        cycle_id=cycle_id,
        error_reason="Simulated connection refusal",
    )

    assert staged_path.exists()
    with open(staged_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["table"] == table
    assert data["operation"] == "INSERT"
    assert data["cycle_id"] == cycle_id
    assert len(data["records"]) == 2
    assert data["records"][0]["value"] == 42.5

    # Cleanup test file
    staged_path.unlink()


def test_db_health_check_structure():
    """Verify that check_db_health returns expected schema without throwing unhandled exceptions."""
    health = check_db_health(timeout=1)
    assert "status" in health
    assert "latency_ms" in health
    assert health["status"] in ("healthy", "unreachable")


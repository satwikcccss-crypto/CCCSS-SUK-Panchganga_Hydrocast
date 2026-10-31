"""
tests/test_postgres_integration.py
==================================
Real-PostgreSQL integration coverage for the orchestrator write path.

These tests are skipped unless ``HYDROCAST_TEST_DATABASE_URL`` is set. CI points
it at a disposable PostGIS service container; no production database is touched.

What this proves that the mocked tests cannot:

* ``database/supabase_schema.sql`` applies cleanly to a plain PostGIS instance
  (including the Supabase-only ``authenticator`` role guard);
* ``create_cycle -> step_start/done -> store_all -> mark_complete`` round-trips
  through a real database;
* ``hydrograph_results``, ``peak_discharge_events`` and ``runoff_summary`` are
  actually written with the expected values;
* a failing step persists ``error_message`` on both the step log and the run.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg2
import psycopg2.extras
import pytest

import src.orchestrator as orch

TEST_DB_URL = os.getenv("HYDROCAST_TEST_DATABASE_URL", "")
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "database" / "supabase_schema.sql"

pytestmark = pytest.mark.skipif(
    not TEST_DB_URL,
    reason="Set HYDROCAST_TEST_DATABASE_URL to run the Postgres integration tests",
)


def _connect():
    return psycopg2.connect(
        TEST_DB_URL,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


@pytest.fixture(scope="session", autouse=True)
def schema():
    """Apply the shipped schema once to the disposable CI database."""
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn = _connect()
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            # The schema creates PostGIS in a dedicated `extensions` schema.
            cur.execute("SET search_path = public, extensions")
            cur.execute(sql)
    finally:
        conn.close()


def test_schema_creates_write_tables_and_api_views():
    """The shipped schema must be able to recreate everything the app reads/writes."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                """
            )
            tables = {row["table_name"] for row in cur.fetchall()}

            cur.execute(
                "SELECT table_name FROM information_schema.views WHERE table_schema = 'public'"
            )
            views = {row["table_name"] for row in cur.fetchall()}

            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'simulation_runs'
                """
            )
            run_columns = {row["column_name"] for row in cur.fetchall()}
    finally:
        conn.close()

    assert {
        "simulation_runs",
        "hydrograph_results",
        "peak_discharge_events",
        "runoff_summary",
        "pipeline_step_log",
        "alert_events",
    } <= tables
    assert {
        "v_latest_hydrograph",
        "v_latest_peak_summary",
        "v_active_alerts_enriched",
        "v_cycle_performance",
    } <= views
    assert "error_message" in run_columns


def _run_dt() -> datetime:
    return datetime(2026, 8, 22, 6, tzinfo=timezone.utc)


def _hydrograph() -> dict:
    start = _run_dt()
    discharges = [100.0, 500.0, 1200.0, 800.0, 400.0, 200.0]
    times = [start + timedelta(hours=i + 1) for i in range(len(discharges))]
    peak = max(discharges)
    return {
        "hydrograph": list(zip(times, discharges)),
        "peak_q": peak,
        "time_of_peak": times[discharges.index(peak)],
        "total_volume_m3": 1_000_000.0,
    }


def _patch_external_steps(monkeypatch) -> dict:
    """Keep step 10 real; stub every network/DSS/alert step around it."""
    hg = _hydrograph()
    monkeypatch.setattr(orch, "DB_URL", TEST_DB_URL)
    monkeypatch.setattr(orch, "get_conn", _connect)
    monkeypatch.setattr(orch, "step1_download_weather", lambda *a, **k: "ds")
    monkeypatch.setattr(orch, "step2_fetch_gauges", lambda *a, **k: None)
    monkeypatch.setattr(orch, "step3_validate", lambda *a, **k: None)
    monkeypatch.setattr(orch, "step4_select_stations", lambda *a, **k: "results")
    monkeypatch.setattr(orch, "step5_write_dss", lambda *a, **k: None)
    monkeypatch.setattr(orch, "step6_check_params", lambda *a, **k: None)
    monkeypatch.setattr(orch, "step7_run_hms", lambda *a, **k: None)
    monkeypatch.setattr(orch, "step8_extract_results", lambda *a, **k: hg)
    monkeypatch.setattr(orch, "step9_stage_conversion", lambda *a, **k: {})
    monkeypatch.setattr(orch, "step11_alerts", lambda *a, **k: None)
    monkeypatch.setattr(orch, "step12_broadcast", lambda *a, **k: None)
    return hg


def test_pipeline_write_path_round_trips(monkeypatch):
    cycle_id = "CYC_PG_TEST_OK"
    _patch_external_steps(monkeypatch)

    orch.run_pipeline(_run_dt(), cycle_id=cycle_id)

    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status, error_message FROM simulation_runs WHERE run_id=%s",
                (cycle_id,),
            )
            run = cur.fetchone()
            assert run["status"] == "completed"
            assert run["error_message"] is None

            cur.execute(
                "SELECT COUNT(*) AS n FROM hydrograph_results WHERE run_id=%s",
                (cycle_id,),
            )
            assert cur.fetchone()["n"] == 6

            cur.execute(
                "SELECT COUNT(*) AS n FROM peak_discharge_events WHERE run_id=%s",
                (cycle_id,),
            )
            assert cur.fetchone()["n"] == 1

            cur.execute(
                "SELECT alert_level, hours_above_emergency FROM runoff_summary WHERE run_id=%s",
                (cycle_id,),
            )
            summary = cur.fetchone()
            assert summary["alert_level"] == "emergency"
            assert summary["hours_above_emergency"] == 1

            cur.execute(
                "SELECT status FROM pipeline_step_log WHERE cycle_id=%s AND step_number=10",
                (cycle_id,),
            )
            assert cur.fetchone()["status"] == "success"
    finally:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM simulation_runs WHERE run_id=%s", (cycle_id,))
        conn.commit()
        conn.close()


def test_failed_step_persists_error_message(monkeypatch):
    cycle_id = "CYC_PG_TEST_FAIL"
    monkeypatch.setattr(orch, "DB_URL", TEST_DB_URL)
    monkeypatch.setattr(orch, "get_conn", _connect)
    monkeypatch.setattr(orch, "step1_download_weather", lambda *a, **k: "ds")
    monkeypatch.setattr(orch, "step2_fetch_gauges", lambda *a, **k: None)

    def _explode(conn, cycle_id, run_dt):
        with orch.timed_step(conn, cycle_id, 3, "Data Validation"):
            raise RuntimeError("QC failed in integration test")

    monkeypatch.setattr(orch, "step3_validate", _explode)

    with pytest.raises(SystemExit) as exc:
        orch.run_pipeline(_run_dt(), cycle_id=cycle_id)
    assert exc.value.code == 1

    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status, error_message FROM simulation_runs WHERE run_id=%s",
                (cycle_id,),
            )
            run = cur.fetchone()
            assert run["status"] == "failed"
            assert "QC failed in integration test" in run["error_message"]

            cur.execute(
                """
                SELECT status, error_message
                FROM pipeline_step_log
                WHERE cycle_id=%s AND step_number=3
                """,
                (cycle_id,),
            )
            step = cur.fetchone()
            assert step["status"] == "failed"
            assert "QC failed in integration test" in step["error_message"]
    finally:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM simulation_runs WHERE run_id=%s", (cycle_id,))
        conn.commit()
        conn.close()

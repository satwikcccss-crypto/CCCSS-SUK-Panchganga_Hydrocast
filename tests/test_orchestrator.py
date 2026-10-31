"""
tests/test_orchestrator.py
==========================
Tests for ``src/orchestrator.py`` — the 12-step production pipeline entry point.

This module was previously at 0% coverage even though it is the code path that
actually runs in production. The tests here use a lightweight psycopg2 connection
double (no database required) to verify:

  * every DB helper writes and commits the expected SQL;
  * ``timed_step`` marks a step running -> success, and running -> failed (+ step_fail)
    when the body raises;
  * ``run_pipeline`` executes all twelve steps in order, then marks the cycle complete;
  * a failing step aborts the cycle with a non-zero exit and still closes the connection.
"""

from datetime import datetime, timezone

import pytest

import src.orchestrator as orch


class _FakeCursor:
    """Records normalised SQL + params; acts as a context manager like psycopg2."""

    def __init__(self, sink):
        self._sink = sink

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self._sink.append((" ".join(sql.split()).upper(), params))


class _FakeConn:
    """Minimal connection double: records SQL, counts commits, tracks close."""

    def __init__(self):
        self.sql = []
        self.commits = 0
        self.closed = False

    def cursor(self, **kwargs):
        return _FakeCursor(self.sql)

    def commit(self):
        self.commits += 1

    def close(self):
        self.closed = True


def _joined(conn):
    return " ".join(s for s, _ in conn.sql)


def _utc():
    return datetime(2026, 8, 22, 6, tzinfo=timezone.utc)


# ─────────────────────────────── DB helpers ───────────────────────────────

def test_step_start_writes_running_row():
    conn = _FakeConn()
    orch.step_start(conn, "CYC_T", 1, "weather")
    assert conn.commits == 1
    assert "INSERT INTO PIPELINE_STEP_LOG" in conn.sql[0][0]
    assert conn.sql[0][1] == ("CYC_T", 1, "weather")


def test_step_done_marks_success_with_details():
    conn = _FakeConn()
    orch.step_done(conn, "CYC_T", 1, {"n": 3})
    assert conn.commits == 1
    assert "STATUS='SUCCESS'" in conn.sql[0][0]
    # details serialised into the params tuple
    assert '{"n": 3}' in conn.sql[0][1]


def test_step_fail_marks_step_and_run_failed():
    conn = _FakeConn()
    orch.step_fail(conn, "CYC_T", 2, "boom")
    assert conn.commits == 1
    joined = _joined(conn)
    assert "STATUS='FAILED'" in joined
    assert "UPDATE SIMULATION_RUNS" in joined
    # error text is passed through (truncated to 2000 chars upstream)
    assert any(p == "boom" for _, params in conn.sql for p in (params or ()))


def test_create_cycle_and_mark_complete():
    conn = _FakeConn()
    orch.create_cycle(conn, "CYC_T", _utc())
    orch.mark_complete(conn, "CYC_T")
    assert conn.commits == 2
    joined = _joined(conn)
    assert "INSERT INTO SIMULATION_RUNS" in joined
    assert "STATUS='COMPLETED'" in joined


# ──────────────────────────────── timed_step ───────────────────────────────

def test_timed_step_success_marks_running_and_no_failure():
    conn = _FakeConn()
    with orch.timed_step(conn, "CYC_T", 3, "validate"):
        pass
    joined = _joined(conn)
    assert "STATUS='RUNNING'" in joined
    # timed_step only opens the step; each step body calls step_done itself.
    assert "STATUS='FAILED'" not in joined


def test_timed_step_failure_calls_step_fail_and_reraises():
    conn = _FakeConn()
    with pytest.raises(RuntimeError):
        with orch.timed_step(conn, "CYC_T", 4, "explode"):
            raise RuntimeError("boom")
    joined = _joined(conn)
    assert "STATUS='RUNNING'" in joined
    assert "STATUS='FAILED'" in joined


# ─────────────────────────────── run_pipeline ──────────────────────────────

_STEP_NAMES = [f"step{i}" for i in range(1, 13)]


def _patch_steps(monkeypatch, calls):
    """Replace all twelve pipeline steps with order-recording stubs.

    Return values are staggered to match what run_pipeline threads through
    (step1 -> ds, step4 -> results, step8 -> hg, step9 -> bfcasts).
    """
    returns = {1: "ds", 4: "results", 8: "hg", 9: "bf"}

    def make(n):
        def _stub(*args, **kwargs):
            calls.append(f"step{n}")
            return returns.get(n)
        return _stub

    monkeypatch.setattr(orch, "step1_download_weather", make(1))
    monkeypatch.setattr(orch, "step2_fetch_gauges", make(2))
    monkeypatch.setattr(orch, "step3_validate", make(3))
    monkeypatch.setattr(orch, "step4_select_stations", make(4))
    monkeypatch.setattr(orch, "step5_write_dss", make(5))
    monkeypatch.setattr(orch, "step6_check_params", make(6))
    monkeypatch.setattr(orch, "step7_run_hms", make(7))
    monkeypatch.setattr(orch, "step8_extract_results", make(8))
    monkeypatch.setattr(orch, "step9_stage_conversion", make(9))
    monkeypatch.setattr(orch, "step10_store_db", make(10))
    monkeypatch.setattr(orch, "step11_alerts", make(11))
    monkeypatch.setattr(orch, "step12_broadcast", make(12))


def test_run_pipeline_executes_twelve_steps_in_order(monkeypatch):
    conn = _FakeConn()
    monkeypatch.setattr(orch, "get_conn", lambda: conn)
    calls = []
    _patch_steps(monkeypatch, calls)

    orch.run_pipeline(_utc(), cycle_id="CYC_T")

    assert calls == _STEP_NAMES
    assert conn.closed is True
    assert "STATUS='COMPLETED'" in _joined(conn)


def test_run_pipeline_failure_exits_nonzero_and_closes(monkeypatch):
    conn = _FakeConn()
    monkeypatch.setattr(orch, "get_conn", lambda: conn)

    def _raise(*args, **kwargs):
        raise RuntimeError("QC failed")

    monkeypatch.setattr(orch, "step1_download_weather", lambda *a, **k: "ds")
    monkeypatch.setattr(orch, "step2_fetch_gauges", lambda *a, **k: None)
    monkeypatch.setattr(orch, "step3_validate", _raise)

    with pytest.raises(SystemExit) as exc:
        orch.run_pipeline(_utc(), cycle_id="CYC_FAIL")

    assert exc.value.code == 1
    assert conn.closed is True

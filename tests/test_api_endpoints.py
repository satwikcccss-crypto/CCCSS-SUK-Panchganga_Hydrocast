"""
tests/test_api_endpoints.py
===========================
HTTP-level coverage for ``src/api/main.py`` (the operator-facing surface).

These are contract tests: they assert response *shapes* and failure modes, not
hydrology. The asyncpg pool is replaced with a tiny deterministic double, so the
suite needs no database and runs in CI on every push.

Coverage target: the read endpoints + validation + security middleware, i.e. the
parts that were previously only reachable in production.
"""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import src.api.main as main
from src.api.main import app
from src.hydrology import ml_calibration, runs_tracker


# ── asyncpg double ────────────────────────────────────────────────────────────

class _Acquire:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *exc):
        return False


class FakePool:
    def __init__(self, conn):
        self._conn = conn

    def acquire(self):
        return _Acquire(self._conn)


class FakeConn:
    def __init__(self, fetch=None, fetchrow=None, fetchval=None):
        self._fetch = list(fetch or [])
        self._fetchrow = fetchrow
        self._fetchval = list(fetchval or [])
        self.executed: list[tuple] = []

    async def fetch(self, *args, **kwargs):
        return self._fetch

    async def fetchrow(self, *args, **kwargs):
        return self._fetchrow

    async def fetchval(self, *args, **kwargs):
        return self._fetchval.pop(0) if self._fetchval else None

    async def execute(self, *args, **kwargs):
        self.executed.append(args)
        return "OK"


def install_pool(monkeypatch, **kwargs) -> FakeConn:
    conn = FakeConn(**kwargs)

    async def fake_get_pool():
        return FakePool(conn)

    monkeypatch.setattr(main, "get_pool", fake_get_pool)
    return conn


@pytest.fixture
def client(monkeypatch):
    # Keep the shared slowapi counter clean for the dedicated rate-limit test.
    monkeypatch.setattr(main.limiter, "enabled", False)
    monkeypatch.setattr(main, "REQUIRE_API_KEY", False)
    monkeypatch.setattr(main, "API_KEY", "")
    return TestClient(app)


# ── health + middleware ───────────────────────────────────────────────────────

def test_health_returns_identity_and_security_headers(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["service"] == "hydrocast-backend"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["cache-control"] == "no-store"


def test_cors_never_reflects_arbitrary_origin_with_credentials(client):
    r = client.get("/api/v1/health", headers={"Origin": "https://evil.example"})
    assert r.headers.get("access-control-allow-origin") in (None, "https://evil.example")
    if r.headers.get("access-control-allow-origin") == "https://evil.example":
        assert r.headers.get("access-control-allow-credentials") != "true"


def test_oversized_body_is_rejected(client):
    r = client.post("/api/v1/visits/record", content=b"x" * 1_100_000)
    assert r.status_code == 413


def test_public_endpoint_requires_api_key(monkeypatch, client):
    install_pool(monkeypatch, fetch=[])
    monkeypatch.setattr(main, "REQUIRE_API_KEY", True)
    monkeypatch.setattr(main, "API_KEY", "unit-test-key")

    assert client.get("/api/v1/alerts").status_code == 401
    assert client.get("/api/v1/alerts", headers={"X-API-Key": "wrong"}).status_code == 401
    ok = client.get("/api/v1/alerts", headers={"X-API-Key": "unit-test-key"})
    assert ok.status_code == 200


# ── status + visits ───────────────────────────────────────────────────────────

def test_status_reports_cycle_and_pipeline_ok(monkeypatch, client):
    install_pool(
        monkeypatch,
        fetchrow={"run_id": "CYC1", "status": "completed"},
        fetchval=[3, True],
    )
    body = client.get("/api/v1/status").json()
    assert body["active_alerts"] == 3
    assert body["pipeline_ok"] is True
    assert body["last_cycle"]["run_id"] == "CYC1"


def test_status_degrades_when_database_is_down(monkeypatch, client):
    async def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(main, "get_pool", boom)
    r = client.get("/api/v1/status")
    assert r.status_code == 200
    assert r.json()["pipeline_ok"] is False
    assert "note" in r.json()


def test_record_visit_counts(monkeypatch, client):
    conn = install_pool(monkeypatch, fetchval=[None, 5, 10])
    body = client.post("/api/v1/visits/record").json()
    assert body == {"daily": 5, "total": 10}
    assert len(conn.executed) == 2  # visitor row + daily counter


# ── rainfall ──────────────────────────────────────────────────────────────────

def test_ecmwf_hyetograph_groups_by_subbasin(monkeypatch, client):
    install_pool(monkeypatch, fetch=[{
        "subbasin_id": "S1",
        "valid_time": datetime(2026, 8, 1, 6, tzinfo=timezone.utc),
        "lead_hours": 1,
        "rainfall_mm_hr": 2.5,
    }])
    body = client.get("/api/v1/rainfall/ecmwf").json()
    assert body["S1"][0]["mm_hr"] == 2.5
    assert body["S1"][0]["hour"] == 1


def test_station_selection_returns_rows(monkeypatch, client):
    install_pool(monkeypatch, fetch=[{"subbasin_id": "S1", "station_name": "G1"}])
    assert client.get("/api/v1/rainfall/stations").json()[0]["station_name"] == "G1"


def test_gauge_hyetographs_returns_rows(monkeypatch, client):
    install_pool(monkeypatch, fetch=[{"gauge_id": "G1", "quality_flag": "ok"}])
    assert client.get("/api/v1/rainfall/gauges").json()[0]["gauge_id"] == "G1"


# ── runoff ────────────────────────────────────────────────────────────────────

def test_outlet_hydrograph_passes_node_filter(monkeypatch, client):
    conn = install_pool(monkeypatch, fetch=[{"lead_hours": 0, "discharge_m3s": 100.0}])
    body = client.get("/api/v1/runoff/hydrograph?outlet_node=J_Outlet").json()
    assert body[0]["discharge_m3s"] == 100.0
    assert conn.executed == []  # SELECT only


def test_runoff_summary_attaches_peak_arrival(monkeypatch, client):
    install_pool(
        monkeypatch,
        fetchrow={"outlet_node": "J_Outlet", "peak_discharge_m3s": 2100.0},
        fetch=[{"site_id": "shivaji", "stage_m": 541.2}],
    )
    monkeypatch.setattr(
        runs_tracker,
        "list_computation_runs",
        lambda limit=1: [{"summary": {"peak_arrival": {"earliest": "t0", "latest": "t1"}}}],
    )
    monkeypatch.setattr(ml_calibration, "calibrator", SimpleNamespace(state={"alpha_k": 0.6}))

    body = client.get("/api/v1/runoff/summary").json()
    assert body["outlet"]["peak_discharge_m3s"] == 2100.0
    assert body["peak_arrival"]["earliest"] == "t0"
    assert body["recalibration"]["alpha_k"] == 0.6


def test_calibration_endpoint_exposes_state(monkeypatch, client):
    monkeypatch.setattr(ml_calibration, "calibrator", SimpleNamespace(state={"alpha_k": 0.6}))
    body = client.get("/api/v1/runoff/calibration").json()
    assert body["calibration"]["alpha_k"] == 0.6
    assert body["status"] == "OPERATIONAL"


def test_stage_forecast_404_for_unknown_site(monkeypatch, client):
    install_pool(monkeypatch, fetch=[], fetchrow=None)
    r = client.get("/api/v1/runoff/stage/unknown")
    assert r.status_code == 404


def test_stage_forecast_returns_metadata_and_series(monkeypatch, client):
    install_pool(
        monkeypatch,
        fetch=[{"lead_hours": 0, "stage_m": 540.0}],
        fetchrow={"site_id": "shivaji", "danger_stage_m": 545.3},
    )
    body = client.get("/api/v1/runoff/stage/shivaji").json()
    assert body["site"]["danger_stage_m"] == 545.3
    assert body["forecast"][0]["stage_m"] == 540.0


# ── alerts + pipeline ─────────────────────────────────────────────────────────

def test_active_alerts_returns_rows(monkeypatch, client):
    install_pool(monkeypatch, fetch=[{"site_id": "shivaji", "alert_level": "WARNING"}])
    assert client.get("/api/v1/alerts").json()[0]["alert_level"] == "WARNING"


def test_flood_bulletin_wraps_sites(monkeypatch, client):
    install_pool(monkeypatch, fetch=[{"site_id": "shivaji", "current_stage": 541.0}])
    body = client.get("/api/v1/alerts/bulletin").json()
    assert body["valid_for_hrs"] == 90
    assert body["sites"][0]["site_id"] == "shivaji"


def test_pipeline_status_returns_steps_and_metrics(monkeypatch, client):
    install_pool(
        monkeypatch,
        fetch=[{"step_number": 1, "status": "success"}],
        fetchrow={"completed": 4, "failed": 0, "avg_duration_s": 12.5},
    )
    body = client.get("/api/v1/pipeline").json()
    assert body["steps"][0]["step_number"] == 1
    assert body["metrics"]["completed"] == 4


def test_cycle_history_returns_rows(monkeypatch, client):
    install_pool(monkeypatch, fetch=[{"run_id": "CYC1"}])
    assert client.get("/api/v1/pipeline/history").json()[0]["run_id"] == "CYC1"


@pytest.mark.parametrize("limit", [0, 9999])
def test_pagination_limit_is_validated(client, limit):
    assert client.get(f"/api/v1/pipeline/history?limit={limit}").status_code == 422


# ── historical runs + accuracy ───────────────────────────────────────────────

def test_list_runs_returns_ledger(monkeypatch, client):
    monkeypatch.setattr(runs_tracker, "list_computation_runs", lambda limit=50: [{"cycle_id": "C1"}])
    assert client.get("/api/v1/runs?limit=5").json()[0]["cycle_id"] == "C1"


def test_list_runs_degrades_to_empty_on_error(monkeypatch, client):
    def boom(limit=50):
        raise RuntimeError("ledger corrupt")

    monkeypatch.setattr(runs_tracker, "list_computation_runs", boom)
    assert client.get("/api/v1/runs").json() == []


def test_get_run_details_404_and_success(monkeypatch, client):
    monkeypatch.setattr(runs_tracker, "get_computation_run", lambda run_id: None)
    assert client.get("/api/v1/runs/C1").status_code == 404

    monkeypatch.setattr(
        runs_tracker,
        "get_computation_run",
        lambda run_id: {"cycle_id": run_id, "summary": {}},
    )
    body = client.get("/api/v1/runs/C1").json()
    assert body["cycle_id"] == "C1"


def test_accuracy_404_when_no_runs(monkeypatch, client):
    monkeypatch.setattr(runs_tracker, "list_computation_runs", lambda limit=1: [])
    assert client.get("/api/v1/accuracy").status_code == 404


def test_accuracy_prefers_stored_validation(monkeypatch, client):
    monkeypatch.setattr(
        runs_tracker,
        "get_computation_run",
        lambda run_id: {"cycle_id": "C1", "validation": {"metrics": {"nse": 0.9}}},
    )
    body = client.get("/api/v1/accuracy?run_id=C1").json()
    assert body["cycle_id"] == "C1"
    assert body["validation"]["metrics"]["nse"] == 0.9


def test_accuracy_computes_when_validation_missing(monkeypatch, client):
    monkeypatch.setattr(
        runs_tracker,
        "get_computation_run",
        lambda run_id: {"cycle_id": "C1", "summary": {"forecast_date": "2026-08-01"}},
    )
    monkeypatch.setattr(
        "src.hydrology.validation_metrics.evaluate_forecast_accuracy",
        lambda run: {"metrics": {"rmse": 0.12}},
    )
    body = client.get("/api/v1/accuracy?run_id=C1").json()
    assert body["validation"]["metrics"]["rmse"] == 0.12


# ── internal broadcast ────────────────────────────────────────────────────────

def test_internal_broadcast_fails_closed(monkeypatch, client):
    monkeypatch.delenv("INTERNAL_KEY", raising=False)
    assert client.post("/internal/broadcast", json={}).status_code == 503

    monkeypatch.setenv("INTERNAL_KEY", "0123456789abcdef")
    assert client.post(
        "/internal/broadcast", json={}, headers={"X-Internal-Key": "wrong"}
    ).status_code == 403
    assert client.post(
        "/internal/broadcast", json={}, headers={"X-Internal-Key": "0123456789abcdef"}
    ).status_code == 200

"""
tests/test_hydrosim_integration.py
==================================
Contract tests for the Hydrosim (HEC-RAS) integration:

* a dedicated consumer key can read public water levels,
* the same key **cannot** reach /admin,
* master key still works,
* JSON and CSV shapes are stable,
* rotation via CONSUMER_API_KEYS works,
* no-cycle returns 404 rather than an empty 200.
"""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import src.api.keys as keys
import src.api.main as main
import src.api.security as security


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
    def __init__(self, run, rows):
        self._run = run
        self._rows = rows

    async def fetchrow(self, *args, **kwargs):
        return self._run

    async def fetch(self, *args, **kwargs):
        return self._rows

    async def fetchval(self, *args, **kwargs):
        return None

    async def execute(self, *args, **kwargs):
        return "OK"


def _row(site: str, lead: int, stage: float) -> dict:
    return {
        "site_id": site,
        "site_name": "Chhatrapati Shivaji Maharaj Bridge",
        "river_name": "Panchganga",
        "latitude": 16.708917,
        "longitude": 74.219278,
        "alert_stage_m": 542.10,
        "warning_stage_m": 542.70,
        "danger_stage_m": 543.30,
        "hfl_m": 545.33,
        "zero_datum_m": 530.18,
        "forecast_time": datetime(2026, 8, 1, 6 + lead, tzinfo=timezone.utc),
        "lead_hours": lead,
        "stage_m": stage,
        "discharge_m3s": 2100.0,
        "alert_level": "WARNING",
        "is_above_danger": False,
    }


RUN = {"run_id": "CYC_20260801_06z", "start_time": datetime(2026, 8, 1, 6, tzinfo=timezone.utc)}
ROWS = [_row("SHIVAJI_BRIDGE", 0, 541.9), _row("SHIVAJI_BRIDGE", 1, 542.4)]


def install(monkeypatch, run=RUN, rows=ROWS):
    conn = FakeConn(run, rows)

    async def fake_get_pool():
        return FakePool(conn)

    monkeypatch.setattr(main, "get_pool", fake_get_pool)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main.limiter, "enabled", False)
    monkeypatch.setattr(main, "REQUIRE_API_KEY", True)
    monkeypatch.setattr(main, "API_KEY", "master-key")
    monkeypatch.setattr(keys, "HYDROCAST_READONLY_KEY", "hydrosim-key")
    monkeypatch.setattr(keys, "HYDROSIM_API_KEY", "")
    monkeypatch.setattr(keys, "_CONSUMER_KEYS", ())
    return TestClient(main.app)


# ── authentication ───────────────────────────────────────────────────────────

def test_hydrosim_key_can_read_water_levels(monkeypatch, client):
    install(monkeypatch)
    r = client.get(
        "/api/v1/integration/hydrosim/stage", headers={"X-API-Key": "hydrosim-key"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["schema_version"] == "1.0"
    assert body["cycle_id"] == "CYC_20260801_06z"
    assert body["units"] == {"stage": "m", "discharge": "m3/s"}
    assert body["sites"][0]["site_id"] == "SHIVAJI_BRIDGE"
    assert body["sites"][0]["thresholds"]["danger_m"] == 543.30
    assert len(body["sites"][0]["series"]) == 2


def test_master_key_still_works(monkeypatch, client):
    install(monkeypatch)
    r = client.get(
        "/api/v1/integration/hydrosim/stage", headers={"X-API-Key": "master-key"}
    )
    assert r.status_code == 200


def test_query_key_accepts_the_master_hydrocast_key(monkeypatch, client):
    # The main HydroCast API_KEY works in the simple URL too.
    install(monkeypatch)
    r = client.get("/api/v1/hydrosim/water-levels?key=master-key")
    assert r.status_code == 200
    assert r.json()["source"] == "HydroCast"


def test_unknown_key_is_rejected(monkeypatch, client):
    install(monkeypatch)
    assert client.get(
        "/api/v1/integration/hydrosim/stage", headers={"X-API-Key": "nope"}
    ).status_code == 401


def test_legacy_hydrosim_env_name_still_works(monkeypatch, client):
    # Existing deployments that still use HYDROSIM_API_KEY keep working.
    monkeypatch.setattr(keys, "HYDROCAST_READONLY_KEY", "")
    monkeypatch.setattr(keys, "HYDROSIM_API_KEY", "legacy-key")
    install(monkeypatch)
    r = client.get("/api/v1/hydrocast/water-levels?key=legacy-key")
    assert r.status_code == 200


def test_query_key_is_accepted_like_open_meteo(monkeypatch, client):
    # The simple, paste-able form: no headers, key inside the URL.
    install(monkeypatch)
    r = client.get("/api/v1/hydrosim/water-levels?key=hydrosim-key")
    assert r.status_code == 200
    assert r.json()["cycle_id"] == "CYC_20260801_06z"


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/hydrocast/water-levels",
        "/api/v1/water-levels",
        "/api/v1/hydrosim/water-levels",
    ],
)
def test_short_aliases_return_the_same_payload(monkeypatch, client, path):
    install(monkeypatch)
    alias = client.get(f"{path}?key=hydrosim-key")
    full = client.get("/api/v1/integration/hydrosim/stage?key=hydrosim-key")
    assert alias.status_code == full.status_code == 200
    assert alias.json() == full.json()


def test_wrong_query_key_is_rejected(monkeypatch, client):
    install(monkeypatch)
    assert client.get("/api/v1/hydrosim/water-levels?key=guess").status_code == 401


def test_query_key_cannot_reach_admin(monkeypatch, client):
    monkeypatch.setattr(security, "API_KEY", "master-key")
    assert client.get("/api/v1/admin/me?key=hydrosim-key").status_code == 401


def test_consumer_key_cannot_reach_admin(monkeypatch, client):
    # The Hydrosim key is read-only; /admin must only accept the master key/JWT.
    monkeypatch.setattr(security, "API_KEY", "master-key")
    assert client.get(
        "/api/v1/admin/me", headers={"X-API-Key": "hydrosim-key"}
    ).status_code == 401
    assert client.get(
        "/api/v1/admin/me", headers={"X-API-Key": "master-key"}
    ).status_code == 200


def test_rotation_list_adds_a_second_key(monkeypatch, client):
    monkeypatch.setattr(keys, "_CONSUMER_KEYS", ("next-key",))
    install(monkeypatch)
    headers = {"X-API-Key": "next-key"}
    assert client.get("/api/v1/integration/hydrosim/stage", headers=headers).status_code == 200
    # The old key remains valid until it is removed from the list.
    assert client.get(
        "/api/v1/integration/hydrosim/stage", headers={"X-API-Key": "hydrosim-key"}
    ).status_code == 200


# ── payload shapes ───────────────────────────────────────────────────────────

def test_csv_format_is_hec_ras_friendly(monkeypatch, client):
    install(monkeypatch)
    r = client.get(
        "/api/v1/integration/hydrosim/stage?format=csv",
        headers={"X-API-Key": "hydrosim-key"},
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "hydrocast_stage_CYC_20260801_06z.csv" in r.headers["content-disposition"]
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("site_id,site_name,forecast_time_utc,lead_hours,stage_m")
    assert len(lines) == 3  # header + two hourly rows


def test_site_filter_is_forwarded(monkeypatch, client):
    install(monkeypatch)
    r = client.get(
        "/api/v1/integration/hydrosim/stage?site_id=SHIVAJI_BRIDGE",
        headers={"X-API-Key": "hydrosim-key"},
    )
    assert r.status_code == 200


def test_no_cycle_returns_404(monkeypatch, client):
    install(monkeypatch, run=None, rows=[])
    r = client.get(
        "/api/v1/integration/hydrosim/stage", headers={"X-API-Key": "hydrosim-key"}
    )
    assert r.status_code == 404


def test_invalid_format_is_422(monkeypatch, client):
    install(monkeypatch)
    r = client.get(
        "/api/v1/integration/hydrosim/stage?format=xml",
        headers={"X-API-Key": "hydrosim-key"},
    )
    assert r.status_code == 422

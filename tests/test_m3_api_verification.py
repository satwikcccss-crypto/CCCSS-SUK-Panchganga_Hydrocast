"""
tests/test_m3_api_verification.py
=================================
Automated regression tests covering Milestone 3 fixes:
- /healthz/ready and /api/v1/ready datetime serialization without 500
- /api/v1/sensors/registry routing precedence before {station_id}
- Prometheus metrics formatting and availability
- Admin /trigger-run duplicate route resolution
- RequestIDMiddleware attached to admin responses
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

import backend.api.main as main
from backend.api.main import app as main_app
from backend.api.admin_app import app as admin_app
from backend.api.observability import _PROMETHEUS_AVAILABLE, generate_latest, CONTENT_TYPE_LATEST


@pytest.fixture
def public_client(monkeypatch):
    monkeypatch.setattr(main.limiter, "enabled", False)
    monkeypatch.setattr(main, "REQUIRE_API_KEY", False)
    monkeypatch.setattr(main, "API_KEY", "")
    return TestClient(main_app)


@pytest.fixture
def admin_client():
    return TestClient(admin_app)


def test_readiness_probe_serializes_datetime_correctly(public_client, monkeypatch):
    """Verify that readiness endpoints handle datetime objects in simulation_runs without 500."""
    class FakeConn:
        async def fetchval(self, *args, **kwargs):
            return 1

        async def fetchrow(self, *args, **kwargs):
            return {
                "status": "completed",
                "start_time": datetime.now(timezone.utc),
            }

    class FakePool:
        def acquire(self):
            class _Acq:
                async def __aenter__(self):
                    return FakeConn()
                async def __aexit__(self, *args):
                    return False
            return _Acq()

    async def fake_get_pool():
        return FakePool()

    monkeypatch.setattr(main, "get_pool", fake_get_pool)
    from backend.api.routes import health
    monkeypatch.setattr(health, "get_pool", fake_get_pool)

    # Test /healthz/ready
    r1 = public_client.get("/healthz/ready")
    assert r1.status_code == 200
    data1 = r1.json()
    assert data1["status"] == "ready"
    assert "start_time" in data1["last_cycle"]
    assert isinstance(data1["last_cycle"]["start_time"], str)

    # Test /api/v1/ready
    r2 = public_client.get("/api/v1/ready")
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["status"] == "ready"


def test_sensors_registry_routing_precedence(public_client):
    """Verify that /api/v1/sensors/registry is not shadowed by /api/v1/sensors/{station_id}."""
    r = public_client.get("/api/v1/sensors/registry")
    assert r.status_code == 200
    data = r.json()
    assert "stations" in data
    assert isinstance(data["stations"], list)
    assert len(data["stations"]) >= 3


def test_prometheus_metrics_format():
    """Verify that prometheus metrics generation produces valid text format."""
    assert _PROMETHEUS_AVAILABLE is True
    output = generate_latest()
    assert isinstance(output, bytes)
    text = output.decode("utf-8")
    assert "# HELP" in text
    assert "# TYPE" in text
    assert "hydrocast_" in text or "python_" in text


def test_admin_request_id_middleware(admin_client):
    """Verify that admin responses carry X-Request-ID."""
    r = admin_client.get("/healthz/live")
    assert r.status_code == 200
    assert "x-request-id" in r.headers
    assert r.headers["x-request-id"].startswith("req_")


def test_admin_trigger_run_and_pipeline_trigger_coexist(admin_client, monkeypatch):
    """Verify that /api/v1/admin/trigger-run and /api/v1/admin/pipeline/trigger both resolve cleanly."""
    from backend.api.security import verify_admin_auth
    from backend.service import scheduler_daemon

    # Prevent real background cycles / global run-lock leakage between tests:
    # the trigger endpoints spawn a background thread that acquires ACTIVE_RUN_LOCK.
    monkeypatch.setattr(
        scheduler_daemon.scheduler_instance,
        "trigger_cycle",
        lambda **kwargs: {"status": "started", "cycle_id": kwargs.get("cycle_id")},
    )

    admin_app.dependency_overrides[verify_admin_auth] = lambda: {"sub": "test_admin", "role": "admin"}
    try:
        # Test /trigger-run
        r1 = admin_client.post(
            "/api/v1/admin/trigger-run",
            json={"async_mode": True},
            headers={"User-Agent": "Mozilla/5.0"}
        )
        assert r1.status_code == 200
        data1 = r1.json()
        assert "cycle_id" in data1
        assert data1["status"] in ("started", "queued", "busy")

        # Test /pipeline/trigger
        r2 = admin_client.post(
            "/api/v1/admin/pipeline/trigger",
            json={"async_mode": True},
            headers={"User-Agent": "Mozilla/5.0"}
        )
        assert r2.status_code == 200
        data2 = r2.json()
        assert data2["ok"] is True
    finally:
        admin_app.dependency_overrides.pop(verify_admin_auth, None)

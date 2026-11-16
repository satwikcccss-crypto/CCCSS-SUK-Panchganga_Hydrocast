"""Regression tests for degraded-mode behaviour in the hydrology routes.

Two production risks are covered here:

1. ``latest_cycle_summary`` is an optional materialized view. When a database
   does not have it, the ECMWF endpoint must fall back to the base table instead
   of returning an empty payload.
2. Cached responses must keep the query string in the cache key, otherwise a
   filtered request can be served another filter's payload.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from starlette.requests import Request

from backend.api.cache import invalidate_response_cache
from backend.api.routes import hydrology


def make_request(path: str = "/api/v1/rainfall/ecmwf", query: str = "") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "query_string": query.encode("latin-1"),
        "headers": [],
        "server": ("testserver", 80),
        "scheme": "http",
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


class _FakeAcquire:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *exc_info):
        return False


class _FakePool:
    def __init__(self, conn):
        self._conn = conn

    def acquire(self):
        return _FakeAcquire(self._conn)


class _ViewMissingConn:
    """Raises for the materialized view, answers for the base table."""

    def __init__(self):
        self.queries: list[str] = []

    async def fetch(self, query, *params):
        self.queries.append(query)
        if "latest_cycle_summary" in query:
            raise RuntimeError('relation "latest_cycle_summary" does not exist')
        return [
            {
                "subbasin_id": "B1",
                "valid_time": datetime(2026, 11, 16, 0, tzinfo=timezone.utc),
                "lead_hours": 0,
                "rainfall_mm_hr": 1.5,
            }
        ]


def test_ecmwf_falls_back_to_base_table_when_view_missing(monkeypatch):
    invalidate_response_cache()
    conn = _ViewMissingConn()

    async def fake_get_pool():
        return _FakePool(conn)

    monkeypatch.setattr(hydrology, "get_pool", fake_get_pool)

    response = asyncio.run(hydrology.ecmwf_hyetograph(make_request()))

    assert response.status_code == 200
    assert any("latest_cycle_summary" in q for q in conn.queries)
    assert any("subbasin_rainfall_ts" in q for q in conn.queries)

    payload = json.loads(response.body)
    assert payload["B1"][0]["mm_hr"] == 1.5


def test_ecmwf_filtered_and_unfiltered_are_cached_separately(monkeypatch):
    invalidate_response_cache()

    class EchoConn:
        async def fetch(self, query, *params):
            subbasin = params[0] if params else "ALL"
            return [
                {
                    "subbasin_id": subbasin,
                    "valid_time": datetime(2026, 11, 16, 0, tzinfo=timezone.utc),
                    "lead_hours": 0,
                    "rainfall_mm_hr": 1.5,
                }
            ]

    async def fake_get_pool():
        return _FakePool(EchoConn())

    monkeypatch.setattr(hydrology, "get_pool", fake_get_pool)

    unfiltered = asyncio.run(hydrology.ecmwf_hyetograph(make_request()))
    filtered = asyncio.run(
        hydrology.ecmwf_hyetograph(make_request(query="subbasin_id=B1"), subbasin_id="B1")
    )

    assert unfiltered.headers["X-Cache"] == "MISS"
    # Different query string => different cache entry, never a HIT of the other.
    assert filtered.headers["X-Cache"] == "MISS"

    unfiltered_payload = json.loads(unfiltered.body)
    filtered_payload = json.loads(filtered.body)
    assert "ALL" in unfiltered_payload
    assert list(filtered_payload) == ["B1"]

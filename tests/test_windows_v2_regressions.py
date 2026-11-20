"""Regression tests for the Windows 2.0.0 stability release.

Each test pins one of the defects found during the full-stack audit so it cannot
silently return:

* ``Decimal`` values must be JSON numbers (the public dashboard used to crash on
  string rainfall values when calling ``.toFixed()``);
* the ThingSpeak client must define its sync fetch functions exactly once and
  must import the modules it uses (``asyncio``/``urllib.request``);
* hydrology and station selection must use the async pipeline-state loader and
  the canonical ``latitude``/``longitude`` columns;
* the runs index must not contain test-cycle artifacts;
* the public API docs page must not advertise endpoints that do not exist.
"""

from __future__ import annotations

import ast
import json
from decimal import Decimal
from pathlib import Path

from starlette.requests import Request

from backend.api.cache import _dumps, cached_json_response, invalidate_response_cache
from backend.api.runtime import compute_etag

REPO_ROOT = Path(__file__).resolve().parents[1]


def _source(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _make_request(path: str = "/api/v1/test") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "query_string": b"",
        "headers": [],
        "server": ("testserver", 80),
        "scheme": "http",
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


# ── JSON numeric integrity ────────────────────────────────────────────────────

def test_decimal_serialises_as_json_number_not_string():
    body = _dumps({"mm_hr": Decimal("0.00"), "stage_m": Decimal("531.84")})
    payload = json.loads(body)

    assert isinstance(payload["mm_hr"], (int, float))
    assert payload["mm_hr"] == 0.0
    assert isinstance(payload["stage_m"], (int, float))
    assert payload["stage_m"] == 531.84
    assert '"mm_hr":"0.00"' not in body.decode("utf-8")


def test_cached_response_emits_numeric_decimal():
    invalidate_response_cache()
    response = cached_json_response(
        _make_request("/api/v1/rainfall/ecmwf"),
        {"S1": [{"mm_hr": Decimal("1.25")}]},
        cache_key="v2-decimal",
    )

    assert json.loads(response.body)["S1"][0]["mm_hr"] == 1.25
    assert response.headers["ETag"].startswith('W/"')


def test_compute_etag_accepts_decimal_payload():
    # Previously ``default=str`` silently changed the hashed representation.
    first = compute_etag({"v": Decimal("2.50")})
    second = compute_etag({"v": Decimal("2.50")})
    assert first == second
    assert first.startswith('W/"')


# ── ThingSpeak client integrity ───────────────────────────────────────────────

def test_multi_station_has_single_sync_definitions():
    tree = ast.parse(_source("backend/thingspeak/multi_station.py"))
    names = [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    assert names.count("fetch_all_stations") == 1
    assert names.count("fetch_station") == 1


def test_multi_station_imports_asyncio_and_urllib():
    tree = ast.parse(_source("backend/thingspeak/multi_station.py"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }

    assert "asyncio" in imported
    assert "urllib.request" in imported


def test_sync_thingspeak_fetch_uses_imported_urllib(monkeypatch):
    """The F821 caught by the release gate would crash this exact path."""
    from backend.thingspeak import multi_station

    class _Response:
        def read(self):
            return b'{"field1":"1.5"}'

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

    captured: dict[str, str] = {}

    def _fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        return _Response()

    monkeypatch.setattr(multi_station.urllib.request, "urlopen", _fake_urlopen)

    result = multi_station._fetch_latest("12345", "test-key", timeout=1)

    assert result == {"field1": "1.5"}
    assert "api_key=test-key" in captured["url"]


# ── Hydrology SQL / loader correctness ────────────────────────────────────────

def test_hydrology_uses_async_loader_and_canonical_columns():
    src = _source("backend/api/routes/hydrology.py")

    assert "await load_pipeline_state_async()" in src
    assert "_load_pipeline_state()" not in src
    assert "ST_Y(g.geom)" not in src
    assert "ST_X(g.geom)" not in src
    assert "g.latitude AS lat, g.longitude AS lon" in src


def test_station_selector_uses_canonical_columns():
    src = _source("backend/rainfall/station_selector.py")

    assert "latitude AS lat, longitude AS lon" in src
    assert "ST_Y(geom)" not in src
    assert "ST_X(geom)" not in src


# ── Data / docs hygiene ───────────────────────────────────────────────────────

def test_runs_index_has_no_test_cycle_artifacts():
    runs = json.loads((REPO_ROOT / "data/runs/runs_index.json").read_text(encoding="utf-8"))
    bad = [r for r in runs if str(r.get("cycle_id", "")).startswith("CYC_TEST_")]

    assert bad == []


def test_docs_page_advertises_only_real_endpoints():
    src = _source("frontend-public/app/docs/page.tsx")

    assert "/api/v1/forecast/latest" not in src
    assert "/api/v1/stations/rainfall" not in src
    assert "/api/v1/runoff/stage/SHIVAJI_BRIDGE" in src
    assert "/api/v1/sensors/registry" in src


# ── Release version consistency ───────────────────────────────────────────────

def test_runtime_version_constants_are_v2():
    from backend.api import admin_app, main

    assert main.app.version == "2.0.0"
    assert admin_app.app.version == "2.0.0"

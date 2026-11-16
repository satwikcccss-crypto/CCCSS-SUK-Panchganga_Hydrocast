"""Regression tests for backend.api.cache.

These cover the defects found during the v1.4.2 production-readiness review:

* cache keys ignored the query string, so ``?subbasin_id=X`` could be served a
  payload cached for the unfiltered request;
* ETag/304 support was advertised but never implemented;
* ``cachetools`` was imported unguarded, so a fresh server could not boot.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from starlette.requests import Request

from backend.api.cache import (
    _SimpleTTLCache,
    cache_key_for,
    cached_json_response,
    invalidate_response_cache,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def make_request(path: str = "/api/v1/test", query: str = "", headers: dict | None = None) -> Request:
    raw_headers = [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in (headers or {}).items()]
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "query_string": query.encode("latin-1"),
        "headers": raw_headers,
        "server": ("testserver", 80),
        "scheme": "http",
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


def test_cache_key_includes_query_string():
    base = cache_key_for(make_request(query=""), namespace="ecmwf")
    filtered = cache_key_for(make_request(query="subbasin_id=B1"), namespace="ecmwf")

    assert base != filtered
    assert "subbasin_id=B1" in filtered


def test_cache_key_is_order_independent():
    first = cache_key_for(make_request(query="a=1&b=2"), namespace="x")
    second = cache_key_for(make_request(query="b=2&a=1"), namespace="x")

    assert first == second


def test_filtered_requests_do_not_share_cached_payload():
    invalidate_response_cache()

    unfiltered = cached_json_response(
        make_request(query=""), {"all": ["B1", "B2"]}, cache_key="ecmwf"
    )
    filtered = cached_json_response(
        make_request(query="subbasin_id=B1"), {"all": ["B1"]}, cache_key="ecmwf"
    )

    assert json.loads(unfiltered.body)["all"] == ["B1", "B2"]
    assert json.loads(filtered.body)["all"] == ["B1"]
    assert filtered.headers["X-Cache"] == "MISS"


def test_repeat_request_is_a_cache_hit():
    invalidate_response_cache()
    request = make_request(query="x=1")

    first = cached_json_response(request, {"value": 1}, cache_key="demo")
    second = cached_json_response(request, {"value": 1}, cache_key="demo")

    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "HIT"
    assert first.headers["ETag"] == second.headers["ETag"]


def test_conditional_request_returns_304():
    invalidate_response_cache()
    request = make_request(query="etag=1")

    first = cached_json_response(request, {"value": 42}, cache_key="etag-demo")
    etag = first.headers["ETag"]
    assert etag.startswith('W/"')

    conditional = make_request(query="etag=1", headers={"if-none-match": etag})
    second = cached_json_response(conditional, {"value": 42}, cache_key="etag-demo")

    assert second.status_code == 304
    assert second.headers["ETag"] == etag
    assert second.body == b""


def test_invalidate_cache_by_namespace():
    invalidate_response_cache()
    request = make_request(query="ns=1")

    cached_json_response(request, {"v": 1}, cache_key="ns-a")
    cached_json_response(request, {"v": 2}, cache_key="ns-b")
    removed = invalidate_response_cache("ns-a")

    assert removed == 1
    # ns-b must still be cached.
    again = cached_json_response(request, {"v": 2}, cache_key="ns-b")
    assert again.headers["X-Cache"] == "HIT"


def test_simple_ttl_cache_expires_entries():
    cache = _SimpleTTLCache(maxsize=2, ttl=0.01)
    cache["k"] = "v"
    assert cache.get("k") == "v"

    import time

    time.sleep(0.02)
    assert cache.get("k") is None


def test_simple_ttl_cache_evicts_when_full():
    cache = _SimpleTTLCache(maxsize=2, ttl=30)
    cache["a"] = 1
    cache["b"] = 2
    cache["c"] = 3

    assert len(list([cache.get("a"), cache.get("b"), cache.get("c")])) == 3
    assert sum(v is not None for v in (cache.get("a"), cache.get("b"), cache.get("c"))) == 2


def test_module_boots_without_cachetools():
    """The API must import and serve even if the optional dependency is absent."""
    code = """
import sys

class BlockCachetools:
    def find_spec(self, name, path=None, target=None):
        if name.split('.')[0] == 'cachetools':
            raise ModuleNotFoundError("No module named 'cachetools'")
        return None

sys.meta_path.insert(0, BlockCachetools())

import backend.api.cache as cache

assert cache._HAS_CACHETOOLS is False
probe = cache._SimpleTTLCache(maxsize=2, ttl=1)
probe['k'] = 'v'
assert probe.get('k') == 'v'
print('ok')
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


@pytest.mark.parametrize(
    "payload",
    [
        {"float": 1.5, "int": 3, "nested": {"ok": True}},
        [1, 2, 3],
        {"unicode": "Panchganga \u2014 \u092a\u093e\u0928\u094d\u091a\u0917\u0902\u0917\u093e"},
    ],
)
def test_serialises_common_payloads(payload):
    invalidate_response_cache()
    response = cached_json_response(make_request(), payload, cache_key="serialise")
    assert json.loads(response.body) == payload

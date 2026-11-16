"""Response caching + JSON serialisation helpers for FastAPI endpoints.

Design notes
------------
* ``cachetools`` and ``orjson`` are **optional**. If either is missing the API
  still boots and serves correct JSON — a fresh deployment must never be taken
  down by an efficiency dependency. ``requirements.txt`` still pins both so the
  fast path is what production actually runs.
* Cache keys include the full request target (path + sorted query string), so a
  filtered request (``?subbasin_id=X``) can never be served a body cached for a
  different filter. This was the original bug in this module.
* ETag / ``If-None-Match`` handling reuses :mod:`backend.api.runtime` so there
  is exactly one implementation of the HTTP caching contract.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import threading
import time
from typing import Any, Optional

from fastapi.responses import Response

from backend.api.runtime import etag_matches

log = logging.getLogger(__name__)

# ── Optional orjson ────────────────────────────────────────────────────────
try:  # pragma: no cover - exercised implicitly by the installed environment
    import orjson

    _HAS_ORJSON = True
except ImportError:  # pragma: no cover
    orjson = None  # type: ignore[assignment]
    _HAS_ORJSON = False

# ── Optional cachetools ────────────────────────────────────────────────────
try:  # pragma: no cover
    from cachetools import TTLCache

    _HAS_CACHETOOLS = True
except ImportError:  # pragma: no cover
    TTLCache = None  # type: ignore[assignment]
    _HAS_CACHETOOLS = False


class _SimpleTTLCache:
    """Minimal lock-protected TTL cache used when ``cachetools`` is absent."""

    def __init__(self, maxsize: int = 128, ttl: float = 30.0) -> None:
        self._data: dict[str, tuple[float, Any]] = {}
        self._maxsize = maxsize
        self._ttl = ttl
        self._lock = threading.Lock()

    def get(self, key: str, default: Any = None) -> Any:
        now = time.monotonic()
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return default
            expires_at, value = item
            if expires_at <= now:
                self._data.pop(key, None)
                return default
            return value

    def __setitem__(self, key: str, value: Any) -> None:
        now = time.monotonic()
        with self._lock:
            if len(self._data) >= self._maxsize and key not in self._data:
                oldest = min(self._data, key=lambda k: self._data[k][0])
                self._data.pop(oldest, None)
            self._data[key] = (now + self._ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


# 128 entries x 30 s is enough to absorb dashboard polling without unbounded growth.
CACHE_TTL_SECONDS = float(os.getenv("PUBLIC_CACHE_TTL_SECONDS", "30"))

_response_cache = (
    TTLCache(maxsize=128, ttl=CACHE_TTL_SECONDS)
    if _HAS_CACHETOOLS
    else _SimpleTTLCache(maxsize=128, ttl=CACHE_TTL_SECONDS)
)

# Bodies larger than this are streamed but not retained in memory.
MAX_CACHED_BODY_BYTES = 2 * 1024 * 1024


# ── Serialisation ──────────────────────────────────────────────────────────
def _dumps(payload: Any) -> bytes:
    """Serialise *payload* to UTF-8 JSON bytes, preferring orjson."""
    if _HAS_ORJSON and orjson is not None:
        try:
            return orjson.dumps(payload, default=str)
        except TypeError:
            pass
    return json.dumps(payload, default=str, separators=(",", ":")).encode("utf-8")


def _weak_etag(body: bytes) -> str:
    """Weak ETag derived from the exact bytes that will be sent."""
    return f'W/"{hashlib.sha256(body).hexdigest()[:32]}"'


# ── Cache keys ─────────────────────────────────────────────────────────────
def cache_key_for(request: Any, namespace: str = "api") -> str:
    """Build a deterministic key from method, path and sorted query string.

    Every query parameter is part of the key: a response for one filter must
    never satisfy a request for another (the previous implementation used a
    bare namespace such as ``"ecmwf"`` and leaked unfiltered payloads).
    """
    url = getattr(request, "url", None)
    if url is None:
        return namespace
    parts = sorted(p for p in str(getattr(url, "query", "") or "").split("&") if p)
    suffix = f"?{'&'.join(parts)}" if parts else ""
    return f"{namespace}:{url.path}{suffix}"


def invalidate_response_cache(namespace: Optional[str] = None) -> int:
    """Drop cached responses (all of them, or just one namespace prefix).

    Call this at the end of a pipeline cycle so the next request sees the new
    forecast rather than waiting out the TTL.
    """
    try:
        if namespace is None:
            _response_cache.clear()
            return -1
        # Both cachetools and the fallback expose dict-like mutation.
        keys = [k for k in _response_cache if str(k).startswith(f"{namespace}:")]
        for key in keys:
            try:
                del _response_cache[key]
            except KeyError:  # pragma: no cover - raced expiry
                pass
        return len(keys)
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("Could not invalidate response cache: %s", exc)
        return 0


# ── Async pipeline-state loader ────────────────────────────────────────────
def _load_pipeline_state() -> Optional[dict]:
    """Read ``data/openmeteo_dss/latest_pipeline_state.json`` from disk."""
    from pathlib import Path

    state_file = (
        Path(__file__).resolve().parents[2]
        / "data"
        / "openmeteo_dss"
        / "latest_pipeline_state.json"
    )
    if state_file.exists():
        try:
            return json.loads(state_file.read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning("Could not parse latest_pipeline_state.json: %s", exc)
    return None


async def load_pipeline_state_async() -> Optional[dict]:
    """Non-blocking wrapper around :func:`_load_pipeline_state`."""
    return await asyncio.to_thread(_load_pipeline_state)


# ── Response helper ────────────────────────────────────────────────────────
def _json_response(
    body: bytes,
    status_code: int,
    etag: str,
    cache_control: str,
    cache_state: str,
) -> Response:
    resp = Response(content=body, status_code=status_code, media_type="application/json")
    resp.headers["ETag"] = etag
    resp.headers["Cache-Control"] = cache_control
    resp.headers["X-Cache"] = cache_state
    return resp


def cached_json_response(
    request: Any,
    payload: Any,
    *,
    cache_key: Optional[str] = None,
    cache_control: str = "public, max-age=30",
    status_code: int = 200,
) -> Response:
    """Return JSON with a weak ETag, 304 support and a short-lived TTL cache.

    Parameters
    ----------
    request:
        Incoming Starlette/FastAPI request; its path and query string are part
        of the cache key and its ``If-None-Match`` header drives 304 responses.
    payload:
        JSON-serialisable response body.
    cache_key:
        Logical namespace (``"ecmwf"``, ``"runoff_summary"`` …). The request
        target is appended automatically, so filtered variants stay distinct.
    """
    key = cache_key_for(request, namespace=cache_key or "response")

    cached = _response_cache.get(key)
    if cached is not None:
        etag, body = cached
        if etag_matches(request, etag):
            return Response(
                status_code=304,
                headers={"ETag": etag, "Cache-Control": cache_control},
            )
        return _json_response(body, status_code, etag, cache_control, "HIT")

    body = _dumps(payload)
    etag = _weak_etag(body)

    if etag_matches(request, etag):
        return Response(
            status_code=304,
            headers={"ETag": etag, "Cache-Control": cache_control},
        )

    if status_code == 200 and len(body) <= MAX_CACHED_BODY_BYTES:
        _response_cache[key] = (etag, body)

    return _json_response(body, status_code, etag, cache_control, "MISS")

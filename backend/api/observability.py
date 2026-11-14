"""Prometheus metrics and HTTP hardening middleware."""

from __future__ import annotations

import logging
import os
import re
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )

    _PROMETHEUS_AVAILABLE = True
except ImportError:
    _PROMETHEUS_AVAILABLE = False
    CONTENT_TYPE_LATEST = "text/plain"
    Counter = Gauge = Histogram = None

    def generate_latest(*args, **kwargs):
        return b""


log = logging.getLogger(__name__)


def _require_api_key() -> bool:
    from backend.api import main

    return bool(main.REQUIRE_API_KEY)


def _public_cache_max_age() -> int:
    from backend.api import main

    return int(main.PUBLIC_CACHE_MAX_AGE)


REQUEST_COUNT = REQUEST_DURATION = REQUESTS_IN_PROGRESS = None

DB_CONNECTIONS = CYCLE_STATUS = ALERT_LEVEL = None

if _PROMETHEUS_AVAILABLE:
    REQUEST_COUNT = Counter(
        "hydrocast_http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status"],
    )
    REQUEST_DURATION = Histogram(
        "hydrocast_http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "endpoint"],
    )
    REQUESTS_IN_PROGRESS = Gauge(
        "hydrocast_http_requests_in_progress",
        "HTTP requests currently being processed",
    )
    DB_CONNECTIONS = Gauge(
        "hydrocast_db_connections",
        "PostgreSQL connection pool status",
        ["state"],
    )
    CYCLE_STATUS = Gauge(
        "hydrocast_forecast_cycle_status",
        "Latest forecast cycle status (1=completed, 0=failed/running)",
        ["status"],
    )
    ALERT_LEVEL = Gauge(
        "hydrocast_alert_level",
        "Current CWC alert level (0=NORMAL,1=ALERT,2=WARNING,3=DANGER,4=HFL_EXCEEDED)",
        ["site"],
    )


_ALERT_LEVEL_MAP = {
    "NORMAL": 0,
    "ALERT": 1,
    "WARNING": 2,
    "DANGER": 3,
    "HFL_EXCEEDED": 4,
}


async def refresh_runtime_gauges() -> None:
    """Best-effort refresh of ops gauges (DB pool, latest cycle, alert levels).

    Called on metrics scrape to keep Prometheus output current without requiring
    background state mutation in request handlers. Failures are swallowed so
    scraping remains reliable during partial outages.
    """
    if not _PROMETHEUS_AVAILABLE:
        return
    try:
        from backend.api.runtime import get_pool
    except Exception:
        return

    # DB pool / cycle status
    try:
        pool = await get_pool()
        if DB_CONNECTIONS is not None:
            if pool is None:
                DB_CONNECTIONS.labels(state="available").set(0)
                DB_CONNECTIONS.labels(state="used").set(0)
                DB_CONNECTIONS.labels(state="size").set(0)
            else:
                size = float(getattr(pool, "get_size", lambda: 0)() or 0)
                idle = float(getattr(pool, "get_idle_size", lambda: 0)() or 0)
                used = max(0.0, size - idle)
                DB_CONNECTIONS.labels(state="available").set(idle)
                DB_CONNECTIONS.labels(state="used").set(used)
                DB_CONNECTIONS.labels(state="size").set(size)

        if pool is not None and CYCLE_STATUS is not None:
            async with pool.acquire() as conn:
                last = await conn.fetchrow(
                    "SELECT status FROM simulation_runs ORDER BY start_time DESC LIMIT 1"
                )
                status = str((last or {}).get("status") or "").lower()
                completed = 1.0 if status in ("completed", "success") else 0.0
                failed = 1.0 if status in ("failed", "error", "aborted") else 0.0
                running = 1.0 if status in ("running", "in_progress", "started") else 0.0
                CYCLE_STATUS.labels(status="completed").set(completed)
                CYCLE_STATUS.labels(status="failed").set(failed)
                CYCLE_STATUS.labels(status="running").set(running)

                if ALERT_LEVEL is not None:
                    # Best-effort: latest alert level per site from most recent cycle forecast rows.
                    try:
                        rows = await conn.fetch(
                            """
                            SELECT DISTINCT ON (site_id)
                                   site_id,
                                   COALESCE(alert_level, 'NORMAL') AS alert_level
                            FROM bridge_stage_forecast
                            ORDER BY site_id, forecast_time DESC
                            """
                        )
                        seen = set()
                        for r in rows or []:
                            site = str(r.get("site_id") or "unknown")
                            lvl = str(r.get("alert_level") or "NORMAL").upper()
                            ALERT_LEVEL.labels(site=site).set(float(_ALERT_LEVEL_MAP.get(lvl, 0)))
                            seen.add(site)
                        # Ensure known sites always emit a value for dashboards.
                        for site in ("SHIVAJI_BRIDGE", "RAJARAM_WEIR"):
                            if site not in seen:
                                ALERT_LEVEL.labels(site=site).set(0.0)
                    except Exception:
                        # Table/schema may vary; do not fail scrape.
                        pass
    except Exception:
        # Never let observability enrichment break /metrics.
        return


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Track HTTP request count, duration, and in-progress gauge for Prometheus."""

    async def dispatch(self, request: Request, call_next):
        if not _PROMETHEUS_AVAILABLE:
            return await call_next(request)
        method = request.method
        endpoint = request.url.path
        REQUESTS_IN_PROGRESS.inc()
        start = time.time()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            # Record failed requests so ops dashboards/alerts see error rates even
            # when downstream handlers raise unexpectedly.
            raise
        finally:
            REQUESTS_IN_PROGRESS.dec()
            duration = time.time() - start
            try:
                REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
                REQUEST_COUNT.labels(
                    method=method, endpoint=endpoint, status=str(status_code)
                ).inc()
            except Exception:
                # Metrics must never break request handling.
                pass


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach hardening headers to every response and reject oversized bodies."""

    MAX_BODY_BYTES = int(os.getenv("MAX_REQUEST_BYTES", str(1_000_000)))

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if (
            content_length
            and content_length.isdigit()
            and int(content_length) > self.MAX_BODY_BYTES
        ):
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body too large"},
            )
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
        if request.url.path.startswith("/api/"):
            cache_control = "no-store"
            # Public-by-default reads are safe to cache only when the API is in
            # zero-key mode: every caller then receives the same public payload.
            # Keyed responses, admin routes, health probes, errors, and writes
            # must never be stored by a shared CDN/browser cache.
            path = request.url.path
            if (
                not _require_api_key()
                and request.method in ("GET", "HEAD")
                and response.status_code == 200
                and path.startswith("/api/v1/")
                and not path.startswith("/api/v1/admin")
                and not path.startswith("/api/v1/health")
            ):
                cache_control = f"public, max-age={_public_cache_max_age()}"
            response.headers.setdefault("Cache-Control", cache_control)
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a validated X-Request-ID to every request/response.

    Client-supplied IDs are accepted only when they are short and use a safe
    header/log character set. Anything else is replaced with a generated ID so
    arbitrary user input can never become a log-injection or header-smuggling
    vector.
    """

    _SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")

    async def dispatch(self, request: Request, call_next):
        supplied = (request.headers.get("X-Request-ID") or "").strip()
        req_id = (
            supplied
            if self._SAFE_REQUEST_ID.fullmatch(supplied)
            else f"req_{uuid.uuid4().hex[:12]}"
        )
        request.state.request_id = req_id
        start = time.time()
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        # Client and server errors carry the request ID in the application log,
        # so a reported response header can be traced back to the exact call.
        if response.status_code >= 400:
            log.warning(
                "%s %s -> %s (%d ms) request_id=%s",
                request.method,
                request.url.path,
                response.status_code,
                int((time.time() - start) * 1000),
                req_id,
            )
        return response


class APIVersionMiddleware(BaseHTTPMiddleware):
    """Add API-Version header to all responses for client version detection."""

    API_VERSION = "1.3.0"

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("API-Version", self.API_VERSION)
        if request.headers.get("Accept-Version"):
            response.headers.setdefault("API-Version-Requested", request.headers["Accept-Version"])
        return response


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


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Track HTTP request count, duration, and in-progress gauge for Prometheus."""

    async def dispatch(self, request: Request, call_next):
        if not _PROMETHEUS_AVAILABLE:
            return await call_next(request)
        method = request.method
        endpoint = request.url.path
        REQUESTS_IN_PROGRESS.inc()
        start = time.time()
        try:
            response = await call_next(request)
        finally:
            REQUESTS_IN_PROGRESS.dec()
            duration = time.time() - start
            REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
            REQUEST_COUNT.labels(
                method=method, endpoint=endpoint, status=str(response.status_code)
            ).inc()
        return response


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

    API_VERSION = "1.1.0"

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("API-Version", self.API_VERSION)
        if request.headers.get("Accept-Version"):
            response.headers.setdefault("API-Version-Requested", request.headers["Accept-Version"])
        return response

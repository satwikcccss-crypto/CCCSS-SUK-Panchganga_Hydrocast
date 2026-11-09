"""
Rainfall-Runoff System — FastAPI Backend
=========================================
Serves all hydrologic data to:
  - Next.js dashboard (same-host or CORS)
  - External consumers via API key and rate-limited public endpoints
  - Disaster management authority administrative endpoints via JWT

Run: uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4

Endpoints
---------
GET /api/v1/health                  health check for Docker & probes
GET /api/v1/status                  system health + current cycle info
GET /api/v1/visits                  persisted daily & total visitor counts
GET /api/v1/rainfall/ecmwf          90-hr ECMWF hyetograph per subbasin
GET /api/v1/rainfall/stations       station selection log for latest cycle
GET /api/v1/rainfall/gauges         all raw gauge hyetographs (last cycle)
GET /api/v1/runoff/hydrograph       outlet discharge hydrograph (90 pts)
GET /api/v1/runoff/summary          peak Q, Tp, volume, stage per bridge
GET /api/v1/runoff/stage/{site_id}  90-hr stage forecast at bridge
GET /api/v1/integration/hydrosim/stage  water-level boundary conditions (JSON/CSV)
GET /api/v1/alerts                  active CWC alerts
GET /api/v1/alerts/bulletin         formatted flood bulletin (PDF-ready JSON)
GET /api/v1/pipeline                pipeline step status for current cycle
GET /api/v1/pipeline/history        last N cycle durations + status
GET /api/v1/runs                    list historical computation runs
GET /api/v1/runs/{run_id}           retrieve computation run details
GET /api/v1/accuracy                validation metrics (NSE, RMSE, Spearman rho)
POST /api/v1/admin/auth/token       admin JWT login
POST /api/v1/admin/trigger-run      manual pipeline cycle trigger
POST /api/v1/admin/archive          cold storage parquet archival
WS  /ws/live                        WebSocket: push on each new cycle result
"""

import os
import sys
import hmac
import json
import csv
import io
import re
import asyncio
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Any

import asyncpg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Header, Request, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi.errors import RateLimitExceeded

load_dotenv()  # must run before src modules read os.environ

from backend.api.admin import router as admin_router  # noqa: E402
from backend.api.limits import limiter, RATE_LIMIT_PUBLIC  # noqa: E402
from backend.api.keys import verify_public_key  # noqa: E402

log = logging.getLogger(__name__)

# ── Rate limiter ──────────────────────────────────────────────────────────────
# The shared instance lives in src.api.limits (also used by the admin login).
app = FastAPI(
    title="HydroCast Panchganga Operational API",
    version="2.0.0",
    summary="Rainfall-runoff and river flood intelligence for the Panchganga Basin, Kolhapur.",
    description=(
        "Operational HTTP and WebSocket API for the **HydroCast** rainfall-runoff "
        "forecasting system.\n\n"
        "It serves a 90-hour forecast horizon driven by ECMWF IFS quantitative "
        "precipitation forecasts over the Panchganga Basin. Nine gauged subbasins "
        "feed an SCS-CN loss / SCS unit-hydrograph / Muskingum cascade "
        "(R1–R5), whose outlet discharge is converted to river stage through a "
        "WRD-anchored PCHIP rating curve at two bridge sites.\n\n"
        "### How to use this reference\n"
        "Everything on this page is generated from the route declarations in "
        "`src/api/main.py` and `src/api/admin.py`. Use **Authorize** in the top "
        "right corner to attach an `X-API-Key` header for public routes, or a JWT "
        "bearer token for administrative routes, then use **Try it out** to call "
        "the live deployment.\n\n"
        "### Access model\n"
        "| Credential | Grants |\n"
        "|:---|:---|\n"
        "| none | `/api/v1/health` only |\n"
        "| `X-API-Key` | all public `/api/v1/*` reads (rate limited) |\n"
        "| JWT (HS256) | `/api/v1/admin/*` — trigger runs, archive, recalibrate |\n"
        "| `X-Internal-Key` | internal broadcast, hidden from this reference |\n\n"
        "### Related documentation\n"
        "* Architecture Atlas — end-to-end system diagrams\n"
        "* Real-Time Runoff Modelling — the hydrology behind the numbers\n"
        "* HEC-HMS Emulator — the calibrated routing engine\n"
        "* API Reference — Python source reference for every module\n\n"
        "Every response time is in **UTC** unless stated otherwise. Discharge is "
        "in **m³/s**, rainfall in **mm/hr**, and stage in **metres above mean sea "
        "level** on the WRD datum."
    ),
    openapi_tags=[
        {"name": "Health & Probes", "description": "Liveness and readiness checks for container orchestration."},
        {"name": "Operations", "description": "Service status, current cycle identity, and pipeline health."},
        {"name": "System", "description": "Anonymous dashboard usage counters."},
        {"name": "Hydrology", "description": "Forecast and observed precipitation: ECMWF areal hyetographs, station selection decisions, raw gauge records."},
        {"name": "Runoff", "description": "Forecast discharge, stage, and the live calibration parameters that produced them."},
        {"name": "Alerts", "description": "Flood alert classification and CWC/DDMA bulletin payloads."},
        {"name": "Pipeline", "description": "Per-step execution status of the 12-step forecast cycle."},
        {"name": "Historical Runs", "description": "Paginated ledger of archived computation cycles."},
        {"name": "Accuracy Validation", "description": "Forecast skill metrics with explicit sample-size gates."},
        {"name": "Admin", "description": "Authenticated operations: manual triggering, cold-storage archival, and forced ML recalibration."},
    ],
    contact={"name": "HydroCast Operations", "url": "https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast"},
    license_info={"name": "Academic research use — DST-SERB funded project"},
)

app.state.limiter = limiter

# Rate limit exception handler with RFC-standard Retry-After header
@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    retry_after = getattr(exc, "retry_after", 60)
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Rate limit exceeded",
            "detail": f"Too many requests. Allowed rate: {RATE_LIMIT_PUBLIC}",
            "retry_after_seconds": retry_after,
        },
        headers={"Retry-After": str(retry_after)},
    )

# ── CORS ──────────────────────────────────────────────────────────────────────
# NEVER combine a wildcard origin with credentials: Starlette would then echo
# the request Origin and set Allow-Credentials, letting any site make
# credentialed cross-origin calls. The dashboard is same-origin (it proxies via
# Next route handlers), so the safe default is an empty allowlist.
_cors_raw = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
# Always allow the local frontend dev servers so direct API calls from the
# public dashboard (port 3000) and admin console (port 3001) work out of the box.
for _default_origin in ("http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001"):
    if _default_origin not in _cors_raw:
        _cors_raw.append(_default_origin)
_cors_wildcard = "*" in _cors_raw
if _cors_wildcard:
    _sec_log = logging.getLogger(__name__)
    _sec_log.critical("CORS_ORIGINS contains '*' — wildcard origins are prohibited. Set explicit allowlist in CORS_ORIGINS.")
    sys.exit(1)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_raw,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Internal-Key", "Cache-Control", "Pragma"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach hardening headers to every response and reject oversized bodies."""

    MAX_BODY_BYTES = int(os.getenv("MAX_REQUEST_BYTES", str(1_000_000)))

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > self.MAX_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body too large"},
            )
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if request.url.path.startswith("/api/"):
            cache_control = "no-store"
            # Public-by-default reads are safe to cache only when the API is in
            # zero-key mode: every caller then receives the same public payload.
            # Keyed responses, admin routes, health probes, errors, and writes
            # must never be stored by a shared CDN/browser cache.
            path = request.url.path
            if (
                not REQUIRE_API_KEY
                and request.method in ("GET", "HEAD")
                and response.status_code == 200
                and path.startswith("/api/v1/")
                and not path.startswith("/api/v1/admin")
                and not path.startswith("/api/v1/health")
            ):
                cache_control = f"public, max-age={PUBLIC_CACHE_MAX_AGE}"
            response.headers.setdefault("Cache-Control", cache_control)
        return response


app.add_middleware(SecurityHeadersMiddleware)


# ── Anti-scraping / Bot-detection middleware ──────────────────────────────────
_BLOCKED_UA_FRAGMENTS = [
    "scrapy", "httpclient", "python-requests", "go-http-client",
    "wget", "curl", "libwww", "java/", "okhttp", "httpx",
    "node-fetch", "undici", "axios", "got ", "superagent",
]
_ALLOWED_BOT_UAS = ["googlebot", "bingbot", "uptimerobot"]

class AntiScrapingMiddleware(BaseHTTPMiddleware):
    """Block automated scraping tools from data endpoints."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api/v1/") or path == "/api/v1/health":
            return await call_next(request)

        ua = (request.headers.get("user-agent") or "").lower()
        if not ua:
            return JSONResponse(
                status_code=403,
                content={"detail": "Forbidden: missing User-Agent"},
            )

        is_known_bot = any(frag in ua for frag in _BLOCKED_UA_FRAGMENTS)
        is_allowed = any(frag in ua for frag in _ALLOWED_BOT_UAS)
        if is_known_bot and not is_allowed:
            return JSONResponse(
                status_code=403,
                content={"detail": "Automated scraping is prohibited. This is a government early warning system."},
            )

        return await call_next(request)


app.add_middleware(AntiScrapingMiddleware)

# Mount Administrative & Control Router (protected by JWT & API Key)
app.include_router(admin_router)

DB_URL = os.getenv("DATABASE_URL", "")
API_KEY = os.getenv("API_KEY", "")
REQUIRE_API_KEY = os.getenv("REQUIRE_API_KEY", "true").lower() == "true"
# Shared-cache lifetime for successful public GETs in zero-key mode. Forecast
# cycles update hourly/6-hourly, so five minutes absorbs monsoon traffic bursts
# while keeping operational freshness. Ignored when REQUIRE_API_KEY is true.
PUBLIC_CACHE_MAX_AGE = int(os.getenv("PUBLIC_CACHE_MAX_AGE", "300"))

# ── DB pool (asyncpg) ─────────────────────────────────────────────────────────

_pool: asyncpg.Pool | None = None
_pool_unavailable: bool = False
_pool_last_attempt: float = 0.0
_POOL_RETRY_SECONDS: float = 30.0

async def get_pool() -> Optional[asyncpg.Pool]:
    """Return the asyncpg pool, or None when PostgreSQL is unreachable.

    Uses a circuit breaker so a missing database doesn't hang every request:
    after a failed attempt, subsequent calls return None immediately for
    _POOL_RETRY_SECONDS before trying again.
    """
    global _pool, _pool_unavailable, _pool_last_attempt
    if _pool is not None:
        try:
            async with _pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return _pool
        except Exception:
            _pool = None

    import time as _time
    now = _time.monotonic()
    if _pool_unavailable and (now - _pool_last_attempt) < _POOL_RETRY_SECONDS:
        return None

    _pool_last_attempt = now
    if not DB_URL:
        _pool_unavailable = True
        return None
    try:
        _pool = await asyncio.wait_for(
            asyncpg.create_pool(DB_URL, min_size=1, max_size=10, command_timeout=10),
            timeout=5.0,
        )
        _pool_unavailable = False
        return _pool
    except Exception as e:
        _pool_unavailable = True
        log.warning("Database pool unavailable: %s", e)
        return None


def _load_pipeline_state() -> Optional[dict]:
    """Load the latest pipeline state JSON for DB-offline fallback."""
    from pathlib import Path
    state_file = Path(__file__).resolve().parents[2] / "data" / "openmeteo_dss" / "latest_pipeline_state.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None

_VISIT_LEDGER_FILE = Path(__file__).resolve().parents[2] / "data" / "visit_ledger.json"
_visit_ledger_lock = asyncio.Lock()


def _load_visit_ledger() -> dict:
    """Load file-based visitor ledger for DB-offline fallback."""
    try:
        if _VISIT_LEDGER_FILE.exists():
            data = json.loads(_VISIT_LEDGER_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "days" in data:
                return data
    except Exception:
        pass
    return {"days": {}, "seen_hashes": {}}


def _save_visit_ledger(ledger: dict) -> None:
    """Persist visitor ledger to disk."""
    try:
        _VISIT_LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
        _VISIT_LEDGER_FILE.write_text(
            json.dumps(ledger, indent=2), encoding="utf-8"
        )
    except Exception as e:
        log.warning("Could not persist visit ledger: %s", e)


def _file_record_visit(ip_hash: str) -> dict:
    """Record a visit in the file-based ledger, returning counts."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ledger = _load_visit_ledger()
    days = ledger.setdefault("days", {})
    seen = ledger.setdefault("seen_hashes", {})
    today_hashes = seen.get(today, [])
    if ip_hash not in today_hashes:
        today_hashes.append(ip_hash)
        seen[today] = today_hashes
        days[today] = days.get(today, 0) + 1
    # Prune hash lists older than 7 days to keep the file small
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    for d in list(seen.keys()):
        if d < cutoff:
            del seen[d]
    _save_visit_ledger(ledger)
    daily = days.get(today, 0)
    total = sum(days.values())
    return {"daily": daily, "total": total}


def _file_read_visits() -> dict:
    """Read visitor counts from the file-based ledger."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ledger = _load_visit_ledger()
    days = ledger.get("days", {})
    daily = days.get(today, 0)
    total = sum(days.values())
    return {"daily": daily, "total": total}


telegram_app = None

@app.on_event("startup")
async def startup():
    pool = await get_pool()
    if pool is not None:
        try:
            log.info("Database connection pool established")
            async with pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS site_visits (
                        visit_date DATE PRIMARY KEY,
                        visit_count INT DEFAULT 1
                    );
                    CREATE TABLE IF NOT EXISTS site_visitor_ips (
                        ip_hash TEXT,
                        visit_date DATE,
                        PRIMARY KEY(ip_hash, visit_date)
                    );
                    CREATE TABLE IF NOT EXISTS admin_users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(64) UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        role VARCHAR(32) NOT NULL DEFAULT 'dev',
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        last_login TIMESTAMPTZ
                    );
                """)
                init_admin = os.getenv("INIT_ADMIN_TABLE", "true").lower() == "true"
                if init_admin:
                    admin_user = os.getenv("ADMIN_USERNAME", "admin")
                    admin_pass = os.getenv("ADMIN_PASSWORD", "")
                    if admin_pass:
                        import bcrypt
                        pw_hash = bcrypt.hashpw(admin_pass.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                        await conn.execute("""
                            INSERT INTO admin_users (username, password_hash, role)
                            VALUES ($1, $2, 'dev')
                            ON CONFLICT (username) DO NOTHING;
                        """, admin_user, pw_hash)
        except Exception as e:
            log.warning("Database initialization failed: %s", e)
    else:
        log.warning("Database offline — API will serve from JSON pipeline state files")

    try:
        from backend.alerts.telegram_bot import build_telegram_application
        global telegram_app
        telegram_app = build_telegram_application()
        if telegram_app:
            await telegram_app.initialize()
            await telegram_app.start()
            await telegram_app.updater.start_polling()
            log.info("Telegram Bot started successfully")
    except Exception as e:
        log.warning(f"Telegram Bot failed to start: {e}")

@app.on_event("shutdown")
async def shutdown():
    if _pool:
        await _pool.close()
    if telegram_app:
        try:
            await telegram_app.updater.stop()
            await telegram_app.stop()
            await telegram_app.shutdown()
            log.info("Telegram Bot stopped")
        except Exception as e:
            log.error(f"Error stopping Telegram Bot: {e}")


# ── Auth & Dependencies ───────────────────────────────────────────────────────

async def verify_public_or_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    If REQUIRE_API_KEY is True, accept either:

    * ``X-API-Key: <key>`` (preferred; never appears in logs), or
    * ``?key=<key>`` (Open-Meteo style, for a simple paste-able URL).

    Fails closed: an unset server key authorises nobody.
    """
    if REQUIRE_API_KEY:
        supplied = x_api_key or request.query_params.get("key") or ""
        if not verify_public_key(supplied, API_KEY or ""):
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key (use X-API-Key header or ?key=)",
            )
    return True

PublicDep = Depends(verify_public_or_key)


# ── WebSocket manager ─────────────────────────────────────────────────────────

class WSManager:
    MAX_CONNECTIONS = int(os.getenv("MAX_WS_CONNECTIONS", "200"))

    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> bool:
        """Accept a socket unless the connection cap is reached (DoS guard)."""
        if len(self.connections) >= self.MAX_CONNECTIONS:
            await ws.close(code=1013)  # 1013 = Try Again Later
            log.warning("WebSocket connection cap (%d) reached — rejecting client", self.MAX_CONNECTIONS)
            return False
        await ws.accept()
        self.connections.append(ws)
        return True

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.connections:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for d in dead:
            if d in self.connections:
                self.connections.remove(d)

ws_manager = WSManager()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _jsonify(rows) -> list[dict]:
    return [dict(r) for r in rows]


# ── Health Probe ──────────────────────────────────────────────────────────────

@app.get(
    "/api/v1/health",
    tags=["Health & Probes"],
    summary="Liveness probe",
    response_description="Service identity, version, and current UTC time.",
)
async def health_check():
    """Liveness probe for Docker healthchecks and monitoring.

    The only endpoint that requires no credential. It touches no database and no
    external service, so a `200` here means *the process is up* — not that the
    forecast pipeline is healthy. Use `/api/v1/status` for pipeline state.
    """
    return {
        "status": "healthy",
        "service": "hydrocast-backend",
        "version": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Operational Endpoints ─────────────────────────────────────────────────────

@app.get(
    "/api/v1/status",
    dependencies=[PublicDep],
    tags=["Operations"],
    summary="Service and pipeline status",
    response_description="Latest cycle record, active alert count, and a 10-of-10 pipeline completion flag.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def system_status(request: Request):
    """Report service status together with the most recent computation cycle.

    `pipeline_ok` is `true` only when the latest cycle logged at least 12
    steps and every one of them carries `status='success'`.

    If the database is unreachable or no cycle has run yet, the endpoint
    degrades gracefully rather than raising: it returns `pipeline_ok: false`
    with an explanatory `note` instead of a `500`.
    """
    try:
        pool = await get_pool()
        if pool is not None:
            async with pool.acquire() as conn:
                last_cycle = await conn.fetchrow("""
                    SELECT run_id, status, start_time, end_time, duration_seconds
                    FROM simulation_runs
                    ORDER BY start_time DESC LIMIT 1
                """)
                active_alerts = await conn.fetchval("SELECT COUNT(*) FROM alert_events WHERE status='active'")
                pipeline_ok   = await conn.fetchval("""
                    SELECT (COUNT(*) >= 12 AND COUNT(*) FILTER (WHERE status <> 'success') = 0)
                    FROM pipeline_step_log
                    WHERE cycle_id=(SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1)
                """)
            return {
                "system":         "operational",
                "last_cycle":     dict(last_cycle) if last_cycle else None,
                "active_alerts":  active_alerts or 0,
                "pipeline_ok":    bool(pipeline_ok),
                "server_time":    datetime.now(timezone.utc).isoformat(),
            }
    except Exception as e:
        log.warning("Status query fallback: %s", e)

    state = _load_pipeline_state()
    if state:
        status_info = state.get("status", {})
        last_cycle_info = status_info.get("last_cycle")
        return {
            "system": "operational",
            "last_cycle": last_cycle_info,
            "active_alerts": 0,
            "pipeline_ok": False,
            "server_time": datetime.now(timezone.utc).isoformat(),
            "note": "Serving from pipeline state file (database offline)",
        }
    return {
        "system": "operational",
        "last_cycle": None,
        "active_alerts": 0,
        "pipeline_ok": False,
        "server_time": datetime.now(timezone.utc).isoformat(),
        "note": "Database offline, no pipeline state available",
    }


@app.post(
    "/api/v1/visits/record",
    dependencies=[PublicDep],
    tags=["System"],
    summary="Record a unique visit",
    response_description="Unique-visitor counts for today and for all time.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def record_visit(request: Request):
    """Records a unique visit and returns today's and total visitor counts.

    The client IP is SHA-256 hashed before it touches the database — the raw
    address is never stored. De-duplication is per UTC day, so a repeat call
    from the same address on the same day increments nothing.
    """
    client_ip = request.client.host if request.client else "unknown"
    _salt = os.getenv("VISIT_HASH_SALT", "")
    if _salt:
        ip_hash = hmac.new(
            _salt.encode("utf-8"), client_ip.encode("utf-8"), hashlib.sha256
        ).hexdigest()
    else:
        # A bare SHA-256 of an IPv4 address is trivially enumerable. Set
        # VISIT_HASH_SALT in production for a non-reversible pseudonym.
        ip_hash = hashlib.sha256(client_ip.encode("utf-8")).hexdigest()
    
    try:
        pool = await get_pool()
        if pool is None:
            counts = _file_record_visit(ip_hash)
            return {**counts, "source": "file"}
        async with pool.acquire() as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM site_visitor_ips WHERE ip_hash=$1 AND visit_date=CURRENT_DATE",
                ip_hash
            )
            if not exists:
                await conn.execute(
                    "INSERT INTO site_visitor_ips (ip_hash, visit_date) VALUES ($1, CURRENT_DATE)",
                    ip_hash
                )
                await conn.execute("""
                    INSERT INTO site_visits (visit_date, visit_count)
                    VALUES (CURRENT_DATE, 1)
                    ON CONFLICT (visit_date) DO UPDATE SET visit_count = site_visits.visit_count + 1
                """)
            daily = await conn.fetchval("SELECT visit_count FROM site_visits WHERE visit_date=CURRENT_DATE")
            total = await conn.fetchval("SELECT SUM(visit_count) FROM site_visits")
        return {"daily": daily or 0, "total": total or 0}
    except Exception as e:
        log.warning("Visit recording fallback: %s", e)
        counts = _file_record_visit(ip_hash)
        return {**counts, "source": "file"}


@app.get(
    "/api/v1/visits",
    dependencies=[PublicDep],
    tags=["System"],
    summary="Read visitor counts",
    response_description="Unique-visitor counts for today and for all time.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def read_visits(request: Request, response: Response):
    """Return the persisted visitor counts without recording a new visit.

    Kept separate from ``POST /api/v1/visits/record`` so dashboards can poll
    for fresh counts (every 60 s) without inflating the daily total. The
    response is explicitly uncacheable so a CDN cannot serve a stale odometer.
    """
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    try:
        pool = await get_pool()
        if pool is None:
            counts = _file_read_visits()
            return {**counts, "source": "file"}
        async with pool.acquire() as conn:
            daily = await conn.fetchval(
                "SELECT visit_count FROM site_visits WHERE visit_date=CURRENT_DATE"
            )
            total = await conn.fetchval("SELECT SUM(visit_count) FROM site_visits")
        return {"daily": daily or 0, "total": total or 0}
    except Exception as e:
        log.warning("Visits fallback: %s", e)
        counts = _file_read_visits()
        return {**counts, "source": "file"}


@app.get(
    "/api/v1/rainfall/ecmwf",
    dependencies=[PublicDep],
    tags=["Hydrology"],
    summary="ECMWF areal hyetograph per subbasin",
    response_description="A map of subbasin id to its 90-point hourly rainfall series (mm/hr).",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def ecmwf_hyetograph(request: Request, subbasin_id: Optional[str] = None):
    """90-hr ECMWF IFS areal rainfall per subbasin (mm/hr, hourly).

    Always reads the **latest** `forecast_run_time` for `source_id='ecmwf_ifs'`,
    so repeated calls never mix two cycles.

    :param subbasin_id: Optional filter. Omit it to return all nine subbasins.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Always fetch latest cycle; optional subbasin filter below
            where = "WHERE forecast_run_time = (SELECT MAX(forecast_run_time) FROM subbasin_rainfall_ts)"
            params: list = []
            if subbasin_id is not None:
                where += f" AND subbasin_id = ${len(params) + 1}"
                params.append(subbasin_id)
            query = f"SELECT subbasin_id, valid_time, lead_hours, rainfall_mm_hr FROM subbasin_rainfall_ts {where} ORDER BY subbasin_id, lead_hours"
            rows = await conn.fetch(query, *params)
    except Exception as e:
        log.warning("ECMWF hyetograph fallback: %s", e)
        state = _load_pipeline_state()
        if state and state.get("ecmwf"):
            return state["ecmwf"]
        return {}

    result: dict[str, list] = {}
    for r in rows:
        sub = r["subbasin_id"]
        result.setdefault(sub, []).append({
            "hour":    r["lead_hours"],
            "time":    r["valid_time"].isoformat(),
            "mm_hr":   r["rainfall_mm_hr"],
        })
    return result


@app.get(
    "/api/v1/rainfall/stations",
    dependencies=[PublicDep],
    tags=["Hydrology"],
    summary="Station selection decisions for the latest cycle",
    response_description="One row per subbasin: the governing gauge, its cumulative rainfall, and the full candidate set.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def station_selection(request: Request):
    """Selection decision for each subbasin in the latest cycle.

    Selection is **database-first**: if a subbasin's governing station has
    readings in the last 90 hours it wins; otherwise the selector falls back to
    the nearest grid cell. `all_candidates_json` carries every station that was
    considered with its distance rank, so a decision can always be audited
    after the fact.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT s.subbasin_id, s.selected_station_id, s.cumulative_mm,
                       s.all_candidates_json, s.selected_at,
                       g.station_name, ST_Y(g.geom) lat, ST_X(g.geom) lon
                FROM station_selection_log s
                JOIN gauge_stations g ON g.station_id=s.selected_station_id
                WHERE s.cycle_id=(SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1)
                ORDER BY s.subbasin_id
            """)
    except Exception as e:
        log.warning("Station selection fallback: %s", e)
        state = _load_pipeline_state()
        if state and state.get("stations"):
            return state["stations"]
        return []
    return _jsonify(rows)


@app.get(
    "/api/v1/rainfall/gauges",
    dependencies=[PublicDep],
    tags=["Hydrology"],
    summary="Raw gauge hyetographs",
    response_description="Every individual gauge record from the last 91 hours, with quality flags and coordinates.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def gauge_hyetographs(request: Request):
    """All individual gauge 90-hr hyetographs for the latest cycle.

    Unlike [`/api/v1/rainfall/ecmwf`](#api-v1-rainfall-ecmwf) — which returns
    the *areal* rainfall chosen per subbasin — this endpoint returns the raw
    per-gauge series for all 18 stations. Use it to audit why a particular
    station was selected.

    `quality_flag` propagates upstream sensor quality and is never filtered
    out; consumers should honour it rather than assuming every row is equally
    trustworthy.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT r.gauge_id, r.subbasin_id, r.timestamp,
                       r.rainfall_mm, r.quality_flag,
                       g.station_name, ST_Y(g.geom) lat, ST_X(g.geom) lon
                FROM rainfall_data r
                JOIN gauge_stations g ON g.station_id=r.gauge_id
                WHERE r.timestamp >= NOW()-'91 hours'::interval
                ORDER BY r.gauge_id, r.timestamp
            """)
    except Exception as e:
        log.warning("Gauge hyetographs fallback: %s", e)
        state = _load_pipeline_state()
        if state and state.get("gauges"):
            return state["gauges"]
        return []
    return _jsonify(rows)


@app.get(
    "/api/v1/runoff/hydrograph",
    dependencies=[PublicDep],
    tags=["Runoff"],
    summary="Outlet discharge hydrograph",
    response_description="90 points of total, surface, and baseflow discharge with stage and peak flags.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def outlet_hydrograph(request: Request, outlet_node: str = "J_Outlet"):
    """90-hr discharge + stage at the sink outlet node.

    The response separates the two physical components so a consumer can reason
    about them separately:

    * `discharge_m3s` — total discharge
    * `surface_runoff_m3s` — the routed surface component from SCS-CN + UH
    * `baseflow_m3s` — exponential recession, floored at the WRD monsoon value
    * `stage_m` — the same discharge pushed through the PCHIP rating curve
    * `is_peak` — `true` on the single `argmax` of total discharge
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT timestamp, lead_hours, discharge_m3s,
                       surface_runoff_m3s, baseflow_m3s, stage_m, is_peak
                FROM v_latest_hydrograph
                WHERE outlet_node=$1
                ORDER BY timestamp
            """, outlet_node)
    except Exception as e:
        log.warning("Outlet hydrograph fallback: %s", e)
        state = _load_pipeline_state()
        if state and state.get("hydrograph"):
            return state["hydrograph"]
        return []
    return _jsonify(rows)


@app.get(
    "/api/v1/runoff/summary",
    dependencies=[PublicDep],
    tags=["Runoff"],
    summary="Peak discharge summary with arrival confidence",
    response_description="Outlet peak statistics, per-bridge forecast series, peak arrival window, and calibration state.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def runoff_summary(request: Request):
    """Peak Q, Tp, volume, flood alert for the latest run with peak arrival confidence intervals.

    Returns data shaped for the frontend dashboard:
    - outlet: peak discharge, time of peak, and runoff volume at the sink
    - summary: same as outlet (for frontend compatibility)
    - bridges: per-bridge stage forecast with thresholds and forecast series
    - hydrograph: 90-hour discharge hydrograph points
    - peak_arrival: calibrated peak arrival times per bridge
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Get latest cycle
            last_cycle = await conn.fetchrow("""
                SELECT run_id, peak_discharge_m3s, lead_hours_to_peak,
                       total_volume_mcm, peak_stage_m, alert_level
                FROM simulation_runs
                ORDER BY start_time DESC LIMIT 1
            """)

            # Get latest stage per bridge with thresholds
            bridge_rows = await conn.fetch("""
                SELECT f.site_id, f.forecast_time, f.stage_m,
                       f.discharge_m3s, f.alert_level,
                       b.site_name, b.alert_stage_m, b.warning_stage_m, b.danger_stage_m, b.hfl_m
                FROM bridge_stage_forecast f
                JOIN bridge_sites b ON b.site_id=f.site_id
                WHERE f.forecast_run_id=(SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1)
                ORDER BY f.site_id, f.forecast_time
            """)

            # Get hydrograph points
            hydro_rows = await conn.fetch("""
                SELECT lead_hours, discharge_m3s, stage_m
                FROM hydrograph_results
                WHERE run_id=(SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1)
                ORDER BY lead_hours ASC
            """)
    except Exception as e:
        log.warning("Runoff summary fallback: %s", e)
        state = _load_pipeline_state()
        if state:
            summary = state.get("summary", {})
            bridges_data = []
            for key in ("bridgeShivaji", "bridgeRajaram"):
                b = state.get(key, {})
                if b:
                    site = b.get("site", {})
                    forecast = b.get("forecast", [])
                    peak_stage = max((f.get("stage_m", 0) for f in forecast), default=0) if forecast else 0
                    bridges_data.append({
                        "site_id": site.get("site_id", key),
                        "site_name": site.get("site_name", key),
                        "alert_stage_m": site.get("alert_stage_m", 0),
                        "warning_stage_m": site.get("warning_stage_m", 0),
                        "danger_stage_m": site.get("danger_stage_m", 0),
                        "hfl_m": site.get("hfl_m", 0),
                        "peak_stage_m": round(peak_stage, 2),
                        "current_stage_m": forecast[0].get("stage_m", 0) if forecast else 0,
                        "stage_m": forecast[0].get("stage_m", 0) if forecast else 0,
                        "alert_level": forecast[0].get("alert_level", "NORMAL") if forecast else "NORMAL",
                        "forecast": forecast,
                    })
            return {
                "outlet": summary.get("outlet", summary) if isinstance(summary, dict) else summary,
                "summary": summary,
                "bridges": bridges_data,
                "hydrograph": state.get("hydrograph", []),
                "peak_arrival": state.get("peak_arrival", summary.get("peak_arrival", {})),
                "recalibration": state.get("recalibration", {}),
            }
        return {
            "outlet": {"peak_discharge_m3s": 0.0, "lead_hours_to_peak": 0,
                       "total_volume_mcm": 0.0, "alert_level": "NORMAL"},
            "summary": {"peak_discharge_m3s": 0.0, "lead_hours_to_peak": 0,
                        "total_volume_mcm": 0.0, "alert_level": "NORMAL"},
            "bridges": [],
            "hydrograph": [],
            "peak_arrival": {},
        }

    if not last_cycle:
        return {
            "outlet": {"peak_discharge_m3s": 0.0, "lead_hours_to_peak": 0,
                       "total_volume_mcm": 0.0, "alert_level": "NORMAL"},
            "summary": {"peak_discharge_m3s": 0.0, "lead_hours_to_peak": 0,
                        "total_volume_mcm": 0.0, "alert_level": "NORMAL"},
            "bridges": [],
            "hydrograph": [],
            "peak_arrival": {},
        }

    # Build bridge objects with full stage data
    bridges_by_site = {}
    for r in bridge_rows:
        sid = r["site_id"]
        if sid not in bridges_by_site:
            # First row's stage_m is the T+0 current stage
            first_stage = None
        sid = r["site_id"]
        if sid not in bridges_by_site:
            first_stage = float(r["stage_m"]) if r.get("stage_m") else None
            bridges_by_site[sid] = {
                "site_id": r["site_id"],
                "site_name": r.get("site_name") or r["site_id"],
                "alert_stage_m": float(r.get("alert_stage_m") or 0),
                "warning_stage_m": float(r.get("warning_stage_m") or 0),
                "danger_stage_m": float(r.get("danger_stage_m") or 0),
                "hfl_m": float(r.get("hfl_m") or 0),
                "peak_stage_m": 0.0,  # will compute after loop
                "alert_level": r.get("alert_level") or "NORMAL",
                "current_stage_m": first_stage if first_stage is not None else 0.0,
                "forecast": [],
            }
        bridges_by_site[sid]["forecast"].append({
            "stage_m": float(r["stage_m"]) if r["stage_m"] else 0.0,
            "lead_hours": int(r["lead_hours"]) if r.get("lead_hours") is not None else 0,
        })

    # Compute per-bridge peak and ensure current_stage_m is the T+0 first point
    bridge_order = ["SHIVAJI_BRIDGE", "RAJARAM_BRIDGE"]
    bridges = []
    for sid in bridge_order:
        if sid in bridges_by_site:
            b = bridges_by_site[sid]
            # True peak = max across all forecast points
            if b["forecast"]:
                b["peak_stage_m"] = max(f["stage_m"] for f in b["forecast"])
                b["current_stage_m"] = b["forecast"][0]["stage_m"]
                b["stage_m"] = b["current_stage_m"]  # backward-compat alias
            bridges.append(b)

    # Build peak_arrival from latest calibration state
    peak_arrival = {}
    try:
        from backend.hydrology.runs_tracker import list_computation_runs
        latest_runs = list_computation_runs(limit=1)
        if latest_runs:
            pa = latest_runs[0].get("summary", {}).get("peak_arrival")
            if pa:
                peak_arrival = {
                    "earliest": pa.get("earliest"),
                    "latest": pa.get("latest"),
                }
    except Exception:
        peak_arrival = {}

    # Get calibration state
    try:
        from backend.ml.ml_calibration import calibrator
        calibration_state = calibrator.state
    except Exception:
        calibration_state = {}

    return {
        "outlet": {
            "peak_discharge_m3s": float(last_cycle.get("peak_discharge_m3s") or 0),
            "lead_hours_to_peak": int(last_cycle.get("lead_hours_to_peak") or 0),
            "total_volume_mcm": float(last_cycle.get("total_volume_mcm") or 0),
            "alert_level": last_cycle.get("alert_level") or "NORMAL",
        },
        "summary": {
            "peak_discharge_m3s": float(last_cycle.get("peak_discharge_m3s") or 0),
            "lead_hours_to_peak": int(last_cycle.get("lead_hours_to_peak") or 0),
            "total_volume_mcm": float(last_cycle.get("total_volume_mcm") or 0),
            "alert_level": last_cycle.get("alert_level") or "NORMAL",
        },
        "bridges": bridges,
        "hydrograph": [
            {
                "lead_hours": int(r.get("lead_hours") or 0),
                "discharge_m3s": float(r["discharge_m3s"]) if r.get("discharge_m3s") is not None else 0.0,
                "stage_m": float(r["stage_m"]) if r.get("stage_m") is not None else 0.0,
            }
            for r in hydro_rows
        ],
        "peak_arrival": peak_arrival,
        "recalibration": calibration_state,
    }


@app.get(
    "/api/v1/runoff/calibration",
    dependencies=[PublicDep],
    tags=["Runoff"],
    summary="Live calibration parameters",
    response_description="Current Curve Number, Muskingum K/X, and subbasin lag with the calibrator's own state.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def hydrologic_calibration(request: Request):
    """Current real-time calibrated hydrologic parameters (Muskingum K & X, Subbasin lag, Curve Number).

    Exposing these makes every forecast self-describing: any client can record
    which parameters produced a given run, so a forecast can be reproduced or
    challenged later.

    The values here are read back from `Basin_1.basin`, which is the single
    source of truth. Recalibration writes that file atomically and keeps a
    timestamped `.bak` alongside it.
    """
    from backend.ml.ml_calibration import calibrator
    return {
        "calibration": calibrator.state,
        "status": "OPERATIONAL",
    }


@app.get(
    "/api/v1/runoff/stage/{site_id}",
    dependencies=[PublicDep],
    tags=["Runoff"],
    summary="Stage forecast at a bridge site",
    response_description="Bridge metadata (thresholds and datum) plus the 90-hour stage and alert series.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def bridge_stage_forecast(request: Request, site_id: str):
    """90-hr stage + alert classification at a bridge site.

    Returns the site's own metadata alongside the series, including the
    `alert`, `warning`, `danger` and `hfl` stage marks, so a consumer never has
    to hard-code thresholds to classify a stage.

    :raises HTTPException 404: if `site_id` is not a known bridge.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT f.forecast_time, f.lead_hours, f.stage_m,
                       f.discharge_m3s, f.alert_level, f.is_above_danger
                FROM bridge_stage_forecast f
                WHERE f.site_id=$1
                  AND f.forecast_run_id=(SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1)
                ORDER BY f.lead_hours
            """, site_id)
            meta = await conn.fetchrow(
                "SELECT * FROM bridge_sites WHERE site_id=$1", site_id
            )
    except Exception as e:
        log.warning("Bridge stage forecast fallback: %s", e)
        state = _load_pipeline_state()
        if state:
            key_map = {"SHIVAJI_BRIDGE": "bridgeShivaji", "RAJARAM_BRIDGE": "bridgeRajaram", "RAJARAM_WEIR": "bridgeRajaram"}
            json_key = key_map.get(site_id)
            if json_key and state.get(json_key):
                b = state[json_key]
                return {"site": b.get("site", {}), "forecast": b.get("forecast", [])}
        raise HTTPException(status_code=404, detail=f"Bridge site '{site_id}' not found")
    if not meta:
        raise HTTPException(status_code=404, detail=f"Bridge site '{site_id}' not found")
    return {
        "site":     dict(meta),
        "forecast": _jsonify(rows),
    }


@app.get(
    "/api/v1/alerts",
    dependencies=[PublicDep],
    tags=["Alerts"],
    summary="Active flood alerts",
    response_description="Every alert currently in the active state, enriched with bridge and threshold context.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def active_alerts(request: Request):
    """List active flood warnings and CWC notifications.

    Only alerts with `status='active'` are returned. Resolved alerts remain
    queryable through the historical runs ledger, so nothing is lost by
    filtering here.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM v_active_alerts_enriched")
    except Exception as e:
        log.warning("Active alerts fallback: %s", e)
        state = _load_pipeline_state()
        if state:
            alerts = state.get("alerts", [])
            if alerts:
                return alerts
            status_info = state.get("status", {})
            last_cycle = status_info.get("last_cycle", {})
            if last_cycle and last_cycle.get("alert_level", "NORMAL") != "NORMAL":
                return [{"alert_level": last_cycle["alert_level"], "site_id": "SYSTEM", "status": "active"}]
        return []
    return _jsonify(rows)


@app.get(
    "/api/v1/alerts/bulletin",
    dependencies=[PublicDep],
    tags=["Alerts"],
    summary="CWC/DDMA flood bulletin payload",
    response_description="A print-ready bulletin per bridge: current stage, trend, HFL margin, and recommended action.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def flood_bulletin(request: Request):
    """Generate CWC-style flood bulletin JSON for all bridge sites.

    Includes: current stage, trend, HFL margin, recommended action.

    This is the payload the Telegram dispatcher forwards to district officers,
    so it is shaped for human reading rather than for plotting — the same data
    in a charting-friendly form is available from
    [`/api/v1/runoff/summary`](#api-v1-runoff-summary).
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT b.site_id, b.site_name,
                       b.alert_stage_m, b.warning_stage_m, b.danger_stage_m, b.hfl_m,
                       f.stage_m AS current_stage,
                       f.discharge_m3s AS current_q,
                       f.alert_level,
                       f.arrival_time,
                       p.peak_discharge_m3s,
                       p.time_of_peak,
                       p.total_runoff_volume_m3
                FROM bridge_sites b
                LEFT JOIN bridge_stage_forecast f ON f.site_id=b.site_id
                    AND f.lead_hours=1
                    AND f.forecast_run_id=(SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1)
                LEFT JOIN peak_discharge_events p ON p.outlet_node='J_Outlet'
                    AND p.run_id=(SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1)
                ORDER BY b.site_id
            """)
    except Exception as e:
        log.warning("Flood bulletin fallback: %s", e)
        rows = []
    issued_at = datetime.now(timezone.utc).isoformat()
    return {
        "bulletin_title": "CWC CENTRAL WATER COMMISSION — FLOOD BULLETIN",
        "issued_at":      issued_at,
        "valid_for_hrs":  90,
        "sites":          _jsonify(rows),
    }


@app.get(
    "/api/v1/pipeline",
    dependencies=[PublicDep],
    tags=["Pipeline"],
    summary="Current cycle step status",
    response_description="Per-step status of the latest cycle, plus 7-day completion/failure counts and mean duration.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def pipeline_status(request: Request):
    """Current cycle pipeline step statuses.

    `error_message` is populated only for failed steps, which is the fastest
    way to tell *where* a cycle broke as well as *that* it broke.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT step_number, step_name, status, start_time, end_time,
                       duration_seconds, error_message
                FROM pipeline_step_log
                WHERE cycle_id=(SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1)
                ORDER BY step_number
            """)
            metrics = await conn.fetchrow("""
                SELECT COUNT(*) FILTER (WHERE status='completed') AS completed,
                       COUNT(*) FILTER (WHERE status='failed')    AS failed,
                       AVG(duration_seconds)                       AS avg_duration_s
                FROM simulation_runs
                WHERE start_time > NOW()-'7 days'::interval
            """)
    except Exception as e:
        log.warning("Pipeline status fallback: %s", e)
        state = _load_pipeline_state()
        if state and state.get("pipeline"):
            p = state["pipeline"]
            return {
                "steps": p.get("steps", []),
                "metrics": p.get("metrics", {}),
            }
        return {"steps": [], "metrics": {}}
    return {
        "steps":   _jsonify(rows),
        "metrics": dict(metrics) if metrics else {},
    }


@app.get(
    "/api/v1/pipeline/history",
    dependencies=[PublicDep],
    tags=["Pipeline"],
    summary="Recent cycle performance",
    response_description="Newest-first list of cycle durations and execution statuses.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def cycle_history(request: Request, limit: int = Query(48, ge=1, le=500)):
    """Last N cycle summaries.

    :param limit: How many cycles to return. Defaults to 48 — twelve days at
        the production cadence of four cycles per day.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM v_cycle_performance
                ORDER BY start_time DESC
                LIMIT $1
            """, limit)
    except Exception as e:
        log.warning("Cycle history fallback: %s", e)
        return []
    return _jsonify(rows)


# ── Historical Runs & Accuracy Validation Endpoints ───────────────────────────

@app.get(
    "/api/v1/dashboard",
    dependencies=[PublicDep],
    tags=["Dashboard"],
    summary="Unified dashboard payload",
    response_description="Live simulation state, ECMWF hyetographs, bridge stages, and historical runs ledger.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def get_dashboard_payload(request: Request, run_id: Optional[str] = None):
    """Serve the complete unified forecast and telemetry payload directly from data/runs or latest pipeline state."""
    from pathlib import Path
    import json
    project_root = Path(__file__).resolve().parents[2]
    
    if run_id:
        from backend.hydrology.runs_tracker import get_computation_run, list_computation_runs
        run_data = get_computation_run(run_id)
        if run_data:
            run_data["runs_history"] = list_computation_runs(limit=100)
            return run_data
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
        
    latest_state = project_root / "data" / "openmeteo_dss" / "latest_pipeline_state.json"
    if latest_state.exists():
        try:
            data = json.loads(latest_state.read_text(encoding="utf-8"))
            from backend.hydrology.runs_tracker import list_computation_runs
            data["runs_history"] = list_computation_runs(limit=100)
            return data
        except Exception as e:
            log.warning("Failed to parse latest_pipeline_state: %s", e)
            
    from backend.hydrology.runs_tracker import list_computation_runs, get_computation_run
    runs = list_computation_runs(limit=1)
    if runs:
        latest = get_computation_run(runs[0]["cycle_id"])
        if latest:
            latest["runs_history"] = list_computation_runs(limit=100)
            return latest
            
    return {"status": {"system": "awaiting_first_run"}, "runs_history": []}


@app.get(
    "/api/v1/runs",
    dependencies=[PublicDep],
    tags=["Historical Runs"],
    summary="List historical computation runs",
    response_description="Newest-first run summaries with KPIs and an accuracy rollup.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def list_runs(request: Request, limit: int = Query(50, ge=1, le=500)):
    """List all tracked historical computation runs with KPIs & accuracy summary.

    :param limit: Maximum number of runs to return. Defaults to 50.
    """
    try:
        from backend.hydrology.runs_tracker import list_computation_runs
        return list_computation_runs(limit=limit)
    except Exception as e:
        log.warning("Failed to list runs: %s", e)
        return []


@app.get(
    "/api/v1/runs/{run_id}",
    dependencies=[PublicDep],
    tags=["Historical Runs"],
    summary="Retrieve one archived run",
    response_description="The complete archived payload for a single simulation cycle.",
    responses={404: {"description": "No run exists with that identifier."}},
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def get_run_details(request: Request, run_id: str):
    """Retrieve full computation payload for a specific historical run.

    :raises HTTPException 404: if `run_id` is not present in the run ledger.
    """
    from backend.hydrology.runs_tracker import get_computation_run
    run = get_computation_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return run


@app.get(
    "/api/v1/accuracy",
    dependencies=[PublicDep],
    tags=["Accuracy Validation"],
    summary="Forecast skill metrics",
    response_description="Skill metrics with the sample-size gates that decided which of them could be computed.",
    responses={404: {"description": "No computation run is available to validate."}},
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def forecast_accuracy(request: Request, run_id: Optional[str] = None):
    """Compute forecast skill for a run.

    Returns Spearman rank correlation, Pearson R², NSE, RMSE, MAE, and
    18-station rainfall volume accuracy.

    ### Why some metrics may be missing

    Metrics are gated on evidence, not reported optimistically:

    * **Error metrics** (RMSE, MAE, PBIAS) are always computable — they need
      only the pairs that exist.
    * **Skill metrics** (NSE, ρ, r²) additionally require at least 6 matched
      hours, a non-degenerate observed series (σ ≥ 0.05 m), and non-zero
      squared deviations (Σ(O−Ō)² > 1e-4). Below those thresholds they are
      omitted with an explicit reason rather than returned as a number that
      would look meaningful but be meaningless.

    Observed "discharge" here is observed **stage** passed through the same
    rating curve that generated the forecast, and is labelled
    `RATING_IMPLIED_DERIVED` accordingly — it is a monotone transform of the
    stage error, not independent evidence of discharge skill.

    :param run_id: Evaluate this run. Defaults to the most recent one.
    """
    from backend.hydrology.runs_tracker import list_computation_runs, get_computation_run
    from backend.validation.validation_metrics import evaluate_forecast_accuracy

    if run_id:
        run = get_computation_run(run_id)
    else:
        runs = list_computation_runs(limit=1)
        run = get_computation_run(runs[0]["cycle_id"]) if runs else None

    if not run:
        raise HTTPException(status_code=404, detail="No computation runs available for validation")

    val = run.get("validation")
    if not val or not val.get("metrics"):
        val = evaluate_forecast_accuracy(run)
    return {
        "cycle_id": run.get("cycle_id"),
        "run_date": run.get("summary", {}).get("forecast_date"),
        "validation": val,
    }


# ── External integration: Hydrosim (HEC-RAS) boundary conditions ─────────────

def _row_get(row, key: str, default=None):
    """Read a column from an asyncpg Record or a plain dict."""
    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        return default


@app.get(
    "/api/v1/water-levels",
    dependencies=[PublicDep],
    tags=["Integration"],
    summary="HydroCast water levels (simplest URL)",
    response_description="Latest forecast stage/discharge series for both bridges (JSON or CSV).",
    responses={404: {"description": "No forecast cycle is available yet."}},
)
@app.get(
    "/api/v1/hydrocast/water-levels",
    dependencies=[PublicDep],
    tags=["Integration"],
    summary="HydroCast-branded water-level URL",
    response_description="Same payload as /api/v1/water-levels.",
    responses={404: {"description": "No forecast cycle is available yet."}},
)
@app.get(
    "/api/v1/hydrosim/water-levels",
    dependencies=[PublicDep],
    tags=["Integration"],
    summary="Hydrosim alias for the water-level feed",
    response_description="Same payload as /api/v1/water-levels.",
    responses={404: {"description": "No forecast cycle is available yet."}},
)
@app.get(
    "/api/v1/integration/hydrosim/stage",
    dependencies=[PublicDep],
    tags=["Integration"],
    summary="Water-level boundary conditions for Hydrosim (HEC-RAS)",
    response_description="90-hour stage series per bridge, with datum/thresholds (JSON or CSV).",
    responses={404: {"description": "No forecast cycle is available yet."}},
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def hydrosim_stage(
    request: Request,
    site_id: Optional[str] = Query(None, max_length=50),
    fmt: str = Query("json", alias="format", pattern="^(json|csv)$"),
):
    """Stage hydrographs shaped for a HEC-RAS unsteady-flow boundary condition.

    **Authentication.** The easiest way is to put the read-only key in the URL
    (Open-Meteo style) and paste it straight into a browser or Python::

        GET /api/v1/hydrocast/water-levels?key=<HYDROCAST_READONLY_KEY>

    The key may also be sent as a header (preferred for production, because
    query strings can appear in access logs)::

        X-API-Key: <HYDROCAST_READONLY_KEY>

    **JSON** (default) returns one object per bridge with metadata, WRD
    thresholds and a hourly ``series``. **CSV** (``?format=csv``) returns the
    long/tidy form that is easy to import as a stage hydrograph::

        site_id,site_name,forecast_time_utc,lead_hours,stage_m,discharge_m3s,alert_level,is_above_danger

    **Datum.** ``stage_m`` is on the WRD gauge datum; ``zero_datum_m`` is the
    site's zero offset. HEC-RAS needs a common vertical datum, so apply
    ``stage_m - zero_datum_m`` (or the datum expected by your geometry) before
    assigning the boundary condition. Do not silently mix datums.

    The series is the *latest* forecast cycle only — never a blend of cycles.
    """
    rows = []
    run = None
    try:
        pool = await get_pool()
        if pool is not None:
            async with pool.acquire() as conn:
                run = await conn.fetchrow(
                    "SELECT run_id, start_time FROM simulation_runs ORDER BY start_time DESC LIMIT 1"
                )
                rows = await conn.fetch(
                    """
                    SELECT f.site_id, b.site_name, b.river_name, b.latitude, b.longitude,
                           b.alert_stage_m, b.warning_stage_m, b.danger_stage_m, b.hfl_m,
                           b.zero_datum_m,
                           f.forecast_time, f.lead_hours, f.stage_m, f.discharge_m3s,
                           f.alert_level, f.is_above_danger
                    FROM bridge_stage_forecast f
                    JOIN bridge_sites b ON b.site_id = f.site_id
                    WHERE f.forecast_run_id = (
                        SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1
                    )
                      AND ($1::text IS NULL OR f.site_id = $1)
                    ORDER BY f.site_id, f.lead_hours
                    """,
                    site_id,
                )
    except Exception as e:
        log.warning("Water levels DB fallback: %s", e)
        state = _load_pipeline_state()
        if state:
            all_forecast = []
            for key in ("bridgeShivaji", "bridgeRajaram"):
                b = state.get(key, {})
                if not b:
                    continue
                s = b.get("site", {})
                sid = s.get("site_id", "")
                if site_id and sid != site_id:
                    continue
                for f in b.get("forecast", []):
                    all_forecast.append({
                        "site_id": sid,
                        "site_name": s.get("site_name", ""),
                        "forecast_time": f.get("forecast_time", ""),
                        "lead_hours": f.get("lead_hours", 0),
                        "stage_m": f.get("stage_m", 0),
                        "discharge_m3s": f.get("discharge_m3s", 0),
                        "alert_level": f.get("alert_level", "NORMAL"),
                        "is_above_danger": f.get("is_above_danger", False),
                    })
            if all_forecast:
                return {"cycle_id": state.get("cycle_id", ""), "issued_at": state.get("run_dt", ""), "sites": all_forecast}

    if not run:
        raise HTTPException(
            status_code=404, detail="No forecast cycle available for Hydrosim yet"
        )

    cycle_id = str(_row_get(run, "run_id", "unknown"))
    start_time = _row_get(run, "start_time")
    issued_at = start_time.isoformat() if hasattr(start_time, "isoformat") else str(start_time)

    if fmt == "csv":
        buf = io.StringIO(newline="")
        writer = csv.writer(buf)
        writer.writerow([
            "site_id", "site_name", "forecast_time_utc", "lead_hours",
            "stage_m", "discharge_m3s", "alert_level", "is_above_danger",
        ])
        for r in rows:
            ft = _row_get(r, "forecast_time")
            writer.writerow([
                _row_get(r, "site_id", ""),
                _row_get(r, "site_name", ""),
                ft.isoformat() if hasattr(ft, "isoformat") else str(ft),
                _row_get(r, "lead_hours", ""),
                _row_get(r, "stage_m", ""),
                _row_get(r, "discharge_m3s", ""),
                _row_get(r, "alert_level", ""),
                bool(_row_get(r, "is_above_danger", False)),
            ])
        safe_id = re.sub(r"[^A-Za-z0-9_.-]", "_", cycle_id)
        return Response(
            content=buf.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="hydrocast_stage_{safe_id}.csv"'
            },
        )

    sites: dict[str, dict] = {}
    for r in rows:
        sid = str(_row_get(r, "site_id", ""))
        site = sites.setdefault(
            sid,
            {
                "site_id": sid,
                "site_name": _row_get(r, "site_name"),
                "river_name": _row_get(r, "river_name"),
                "latitude": _row_get(r, "latitude"),
                "longitude": _row_get(r, "longitude"),
                "zero_datum_m": _row_get(r, "zero_datum_m"),
                "thresholds": {
                    "alert_m": _row_get(r, "alert_stage_m"),
                    "warning_m": _row_get(r, "warning_stage_m"),
                    "danger_m": _row_get(r, "danger_stage_m"),
                    "hfl_m": _row_get(r, "hfl_m"),
                },
                "series": [],
            },
        )
        ft = _row_get(r, "forecast_time")
        site["series"].append(
            {
                "forecast_time": ft.isoformat() if hasattr(ft, "isoformat") else str(ft),
                "lead_hours": _row_get(r, "lead_hours"),
                "stage_m": _row_get(r, "stage_m"),
                "discharge_m3s": _row_get(r, "discharge_m3s"),
                "alert_level": _row_get(r, "alert_level"),
                "is_above_danger": bool(_row_get(r, "is_above_danger", False)),
            }
        )

    return {
        "schema_version": "1.0",
        "source": "HydroCast",
        "cycle_id": cycle_id,
        "issued_at": issued_at,
        "units": {"stage": "m", "discharge": "m3/s"},
        "vertical_datum": (
            "WRD gauge datum; zero_datum_m is the site zero offset. "
            "Align to your HEC-RAS geometry datum before use."
        ),
        "sites": list(sites.values()),
    }


# ── WebSocket live push ────────────────────────────────────────────────────────

@app.websocket(
    "/ws/live",
    name="live_cycle_push",
)
async def ws_live(websocket: WebSocket):
    """Push new data to connected dashboards after each completed cycle.

    The pipeline orchestrator calls `ws_manager.broadcast()` after step 12.
    Dead connections are detected on send and reaped automatically, so a
    browser that vanishes mid-cycle does not block the remaining subscribers.
    """
    if not await ws_manager.connect(websocket):
        return
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.post("/internal/broadcast", include_in_schema=False)
async def internal_broadcast(payload: dict, x_internal_key: str = Header(None)):
    """Called by orchestrator after each successful cycle. Not public."""
    _ik = os.getenv("INTERNAL_KEY", "")
    if len(_ik) < 16:
        # Fail closed: a short/empty shared secret is not an acceptable credential.
        raise HTTPException(status_code=503, detail="Internal auth not configured")
    supplied = str(x_internal_key or "")
    if not hmac.compare_digest(supplied.encode("utf-8"), _ik.encode("utf-8")):
        raise HTTPException(status_code=403, detail="Invalid internal key")
    await ws_manager.broadcast(payload)
    return {"broadcast_to": len(ws_manager.connections)}


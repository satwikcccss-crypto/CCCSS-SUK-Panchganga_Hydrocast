"""
Rainfall-Runoff System â€” FastAPI Backend
=========================================
Serves all hydrologic data to:
  - Next.js dashboard (same-host or CORS)
  - External consumers via API key and rate-limited public endpoints
  - Disaster management authority administrative endpoints via JWT

Run: uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --workers 4

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
import asyncio
import logging
from typing import Optional

import asyncpg
from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

load_dotenv()  # must run before backend modules read os.environ

from backend.api.admin import router as admin_router  # noqa: E402
from backend.api.routes.health import router as health_router  # noqa: E402
from backend.api.routes.sensors import router as sensors_router  # noqa: E402
from backend.api.routes.integration import router as integration_router  # noqa: E402
from backend.api.routes.pipeline import router as pipeline_router  # noqa: E402
from backend.api.routes.hydrology import router as hydrology_router  # noqa: E402
from backend.api.limits import limiter, RATE_LIMIT_PUBLIC  # noqa: E402
from backend.api.observability import (
    APIVersionMiddleware,
    PrometheusMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)

log = logging.getLogger(__name__)

# â”€â”€ OpenAPI docs visibility â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# In production, /docs and /openapi.json are disabled so the API surface is
# not exposed to unautomated reconnaissance. In dev/test they remain available
# for local development. Override with APP_ENV=dev to keep docs in production.
_APP_ENV_DOCS = os.getenv("APP_ENV", "production").lower()
_docs_url = None if _APP_ENV_DOCS == "production" else "/docs"
_openapi_url = None if _APP_ENV_DOCS == "production" else "/openapi.json"

# â”€â”€ Rate limiter â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# The shared instance lives in backend.api.limits (also used by the admin login).
app = FastAPI(
    version="1.2.0",
    summary="Rainfall-runoff and river flood intelligence for the Panchganga Basin, Kolhapur.",
    docs_url=_docs_url,
    openapi_url=_openapi_url,
    description=(
        "Operational HTTP and WebSocket API for the **HydroCast** rainfall-runoff "
        "forecasting system.\n\n"
        "It serves a 90-hour forecast horizon driven by ECMWF IFS quantitative "
        "precipitation forecasts over the Panchganga Basin. Nine gauged subbasins "
        "feed an SCS-CN loss / SCS unit-hydrograph / Muskingum cascade "
        "(R1â€“R5), whose outlet discharge is converted to river stage through a "
        "WRD-anchored PCHIP rating curve at two bridge sites.\n\n"
        "### How to use this reference\n"
        "Everything on this page is generated from the route declarations in "
        "`backend/api/routes/` and `backend/api/admin_routes/`. Use **Authorize** in the top "
        "right corner to attach an `X-API-Key` header for public routes, or a JWT "
        "bearer token for administrative routes, then use **Try it out** to call "
        "the live deployment.\n\n"
        "### Access model\n"
        "| Credential | Grants |\n"
        "|:---|:---|\n"
        "| none | `/api/v1/health` only |\n"
        "| `X-API-Key` | all public `/api/v1/*` reads (rate limited) |\n"
        "| JWT (HS256) | `/api/v1/admin/*` â€” trigger runs, archive, recalibrate |\n"
        "| `X-Internal-Key` | internal broadcast, hidden from this reference |\n\n"
        "### Related documentation\n"
        "* Architecture Atlas â€” end-to-end system diagrams\n"
        "* Real-Time Runoff Modelling â€” the hydrology behind the numbers\n"
        "* HEC-HMS Emulator â€” the calibrated routing engine\n"
        "* API Reference â€” Python source reference for every module\n\n"
        "Every response time is in **UTC** unless stated otherwise. Discharge is "
        "in **mÂ³/s**, rainfall in **mm/hr**, and stage in **metres above mean sea "
        "level** on the WRD datum."
    ),
    openapi_tags=[
        {
            "name": "Health & Probes",
            "description": "Liveness and readiness checks for container orchestration.",
        },
        {
            "name": "Operations",
            "description": "Service status, current cycle identity, and pipeline health.",
        },
        {"name": "System", "description": "Anonymous dashboard usage counters."},
        {
            "name": "Hydrology",
            "description": "Forecast and observed precipitation: ECMWF areal hyetographs, station selection decisions, raw gauge records.",
        },
        {
            "name": "Runoff",
            "description": "Forecast discharge, stage, and the live calibration parameters that produced them.",
        },
        {"name": "Alerts", "description": "Flood alert classification and bulletin payloads."},
        {
            "name": "Pipeline",
            "description": "Per-step execution status of the 12-step forecast cycle.",
        },
        {
            "name": "Historical Runs",
            "description": "Paginated ledger of archived computation cycles.",
        },
        {
            "name": "Accuracy Validation",
            "description": "Forecast skill metrics with explicit sample-size gates.",
        },
        {
            "name": "Admin",
            "description": "Authenticated operations: manual triggering, cold-storage archival, and forced ML recalibration.",
        },
    ],
    contact={
        "name": "HydroCast Operations",
        "url": "https://github.com/satwikcccss-crypto/CCCSS-SUK-Panchganga_Hydrocast",
    },
    license_info={"name": "Academic research use â€” DST-SERB funded project"},
)

app.state.limiter = limiter


# â”€â”€ Custom OpenAPI Schema (Public Read-Only Sanitization) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def custom_openapi():
    """
    Sanitize the public OpenAPI reference.
    Exposes strictly the free, open-access public flood intelligence endpoint
    and the service health check. All internal pipeline, simulation,
    and administrative endpoints are stripped to protect system internals.
    """
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title="Shivaji University Kolhapur â€” HydroCast Public Flood Intelligence API",
        version="1.2.0",
        description=(
            "### Official Free Public Flood Intelligence API\n"
            "Centre for Climate Change and Sustainability Studies (CCCSS), Shivaji University, Kolhapur.\n\n"
            "**100% Free & Open Access â€” No API Key Required.**\n\n"
            "Serves real-time 90-hour river stages (Shivaji Bridge & Rajaram Weir), "
            "basin discharge hydrograph, and 20-station rainfall intelligence.\n\n"
            "**Anti-Scraping & Fair Use Protection:**\n"
            "- High-speed in-memory caching (20s TTL) for sub-millisecond responses.\n"
            "- Rate-limited to 60 requests/minute per client IP.\n"
            "- Cache-Control: `public, max-age=20`."
        ),
        routes=app.routes,
    )

    allowed_endpoints = {"/api/SUK_hydrocast_v1", "/api/v1/health"}
    filtered_paths = {}

    for path, methods in schema.get("paths", {}).items():
        if path in allowed_endpoints:
            for method, details in methods.items():
                details["tags"] = ["Free Public Flood API"]
                details.pop("security", None)
            filtered_paths[path] = methods

    schema["paths"] = filtered_paths
    schema["tags"] = [
        {
            "name": "Free Public Flood API",
            "description": "Free, read-only flood intelligence feeds for public and researchers.",
        }
    ]
    if "components" in schema:
        schema["components"].pop("securitySchemes", None)
    schema.pop("security", None)

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi


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


# â”€â”€ CORS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# NEVER combine a wildcard origin with credentials: Starlette would then echo
# the request Origin and set Allow-Credentials, letting any site make
# credentialed cross-origin calls. The dashboard is same-origin (it proxies via
# Next route handlers), so the safe default is an empty allowlist.
_cors_raw = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
# Always allow the local frontend dev servers so direct API calls from the
# public dashboard (port 3000) and admin console (port 3001) work out of the box.
for _default_origin in (
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
):
    if _default_origin not in _cors_raw:
        _cors_raw.append(_default_origin)
_cors_wildcard = "*" in _cors_raw
if _cors_wildcard:
    _sec_log = logging.getLogger(__name__)
    _sec_log.critical(
        "CORS_ORIGINS contains '*' â€” wildcard origins are prohibited. Set explicit allowlist in CORS_ORIGINS."
    )
    sys.exit(1)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_raw,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-API-Key",
        "X-Internal-Key",
        "Cache-Control",
        "Pragma",
    ],
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(PrometheusMiddleware)

app.add_middleware(APIVersionMiddleware)

# Mount Administrative & Control Router (protected by JWT & API Key)
app.include_router(admin_router)
app.include_router(health_router)
app.include_router(sensors_router)
app.include_router(integration_router)
app.include_router(pipeline_router)
app.include_router(hydrology_router)

DB_URL = os.getenv("DATABASE_URL", "")
API_KEY = os.getenv("API_KEY", "")
REQUIRE_API_KEY = os.getenv("REQUIRE_API_KEY", "true").lower() == "true"
# Shared-cache lifetime for successful public GETs in zero-key mode. Forecast
# cycles update hourly/6-hourly, so five minutes absorbs monsoon traffic bursts
# while keeping operational freshness. Ignored when REQUIRE_API_KEY is true.
PUBLIC_CACHE_MAX_AGE = int(os.getenv("PUBLIC_CACHE_MAX_AGE", "300"))

# â”€â”€ DB pool (asyncpg) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

                        pw_hash = bcrypt.hashpw(
                            admin_pass.encode("utf-8"), bcrypt.gensalt()
                        ).decode("utf-8")
                        await conn.execute(
                            """
                            INSERT INTO admin_users (username, password_hash, role)
                            VALUES ($1, $2, 'dev')
                            ON CONFLICT (username) DO NOTHING;
                        """,
                            admin_user,
                            pw_hash,
                        )
        except Exception as e:
            log.warning("Database initialization failed: %s", e)
    else:
        log.warning("Database offline â€” API will serve from JSON pipeline state files")

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


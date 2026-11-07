"""
backend/api/admin_app.py
========================
Operator Console FastAPI API for HydroCast Panchganga — Port 8001.

Impenetrable admin console backend. Strictly protected by local PostgreSQL RBAC
(bcrypt) and HS256 JWT. Features:

  - POST /api/v1/admin/auth/token    admin JWT login
  - GET  /api/v1/admin/me            current identity and claims
  - POST /api/v1/admin/trigger-run   manually execute a forecast cycle
  - POST /api/v1/admin/archive       Parquet cold-storage archival
  - POST /api/v1/admin/recalibrate   forced ML recalibration and basin sync
  - GET  /api/v1/admin/pipeline      12-step matrix with live status & durations
  - POST /api/v1/admin/abort         emergency abort
  - POST /api/v1/admin/pause         pause/resume scheduler
  - POST /api/v1/admin/backup-db     manual database backup
  - GET  /api/v1/admin/health        admin service health
  - WS  /ws/admin/logs               streaming operator logs

Access model: JWT bearer token (HS256) or master X-API-Key.
No public read routes are exposed here — those live on the Public API (Port 8000).
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional

import asyncpg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Header, Request, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi.errors import RateLimitExceeded

load_dotenv()

from backend.api.admin import router as admin_router  # noqa: E402
from backend.api.limits import limiter, RATE_LIMIT_LOGIN  # noqa: E402
from backend.api.security import verify_admin_auth  # noqa: E402

log = logging.getLogger(__name__)

app = FastAPI(
    title="HydroCast Panchganga Operator Console API",
    version="2.0.0",
    summary="Operator Console administrative API (Port 8001)",
    description=(
        "**IMPENETRABLE ADMIN CONSOLE** — HydroCast operator control plane.\n\n"
        "Every route requires authentication. Two credentials are accepted:\n"
        "| Credential | Grants |\n"
        "|:---|:---|\n"
        "| JWT bearer (HS256) | full admin control |\n"
        "| master X-API-Key | service-to-service automation |\n\n"
        "Routes:\n"
        "- `POST /api/v1/admin/auth/token` — exchange admin credentials for JWT\n"
        "- `GET /api/v1/admin/me` — current identity and role claims\n"
        "- `POST /api/v1/admin/trigger-run` — manually execute forecast cycle\n"
        "- `POST /api/v1/admin/archive` — cold-storage Parquet archival\n"
        "- `POST /api/v1/admin/recalibrate` — forced ML recalibration\n"
        "- `GET /api/v1/admin/pipeline` — 12-step matrix with live status\n"
        "- `POST /api/v1/admin/abort` — emergency abort\n"
        "- `POST /api/v1/admin/pause` — pause/resume scheduler\n"
        "- `POST /api/v1/admin/backup-db` — manual database backup\n"
        "- `GET /api/v1/admin/health` — admin service health\n"
        "- `WS /ws/admin/logs` — streaming operator logs over WebSocket\n\n"
        "This port (8001) is **isolated from the public portal** (Port 8000). "
        "No citizen or DDMA read routes are exposed here."
    ),
    openapi_tags=[
        {"name": "Admin Auth", "description": "JWT login and identity."},
        {"name": "Admin Control", "description": "Pipeline trigger, abort, pause, backup."},
        {"name": "Admin Health", "description": "Operator console service health."},
    ],
    contact={"name": "HydroCast Operations — Admin"},
    license_info={"name": "Academic research use — DST-SERB funded project"},
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    retry_after = getattr(exc, "retry_after", 60)
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Rate limit exceeded",
            "detail": f"Admin rate limit: {RATE_LIMIT_LOGIN}",
            "retry_after_seconds": retry_after,
        },
        headers={"Retry-After": str(retry_after)},
    )


# ── CORS (admin console same-origin only) ──────────────────────────────────────

_cors_raw = [o.strip() for o in os.getenv("ADMIN_CORS_ORIGINS", "").split(",") if o.strip()]
_cors_wildcard = "*" in _cors_raw

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _cors_wildcard else _cors_raw,
    allow_credentials=not _cors_wildcard,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


class AdminSecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach hardening headers to every admin response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        response.headers.setdefault("Cache-Control", "no-store, no-cache, must-revalidate, private")
        return response


app.add_middleware(AdminSecurityHeadersMiddleware)


# ── Config ─────────────────────────────────────────────────────────────────────

DB_URL = os.getenv("DATABASE_URL", "")
API_KEY = os.getenv("API_KEY", "")
JWT_SECRET = os.getenv("JWT_SECRET", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

if not JWT_SECRET:
    log.warning("JWT_SECRET is not set — JWT authentication will reject all tokens.")
if not ADMIN_PASSWORD:
    log.warning("ADMIN_PASSWORD is not set — admin login will be disabled.")

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DB_URL, min_size=2, max_size=10)
    return _pool


# ── Auth Dependency ────────────────────────────────────────────────────────────

async def verify_admin_or_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    """Require JWT bearer or master API key for all admin routes."""
    # Check JWT
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        # Use existing security module for JWT verification
        from backend.api.security import verify_access_token
        try:
            payload = verify_access_token(token)
            if payload:
                return True
        except Exception:
            pass

    # Check master API key
    if x_api_key and API_KEY and x_api_key == API_KEY:
        return True

    raise HTTPException(
        status_code=401,
        detail="Admin authentication required (JWT bearer or X-API-Key)",
    )


AdminDep = Depends(verify_admin_or_key)


# Mount the admin router (all routes under /api/v1/admin)
app.include_router(admin_router)


# ── Admin-Only Routes ──────────────────────────────────────────────────────────

@app.get(
    "/api/v1/admin/health",
    tags=["Admin Health"],
    summary="Admin service health",
)
async def admin_health(request: Request, _: bool = AdminDep):
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unreachable: {e}"

    return {
        "service": "hydrocast-admin-console",
        "version": "2.0.0",
        "port": 8001,
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "auth": {
            "jwt_configured": bool(JWT_SECRET),
            "admin_password_configured": bool(ADMIN_PASSWORD),
        },
    }


@app.post(
    "/api/v1/admin/abort",
    tags=["Admin Control"],
    summary="Emergency abort active forecast cycle",
)
async def admin_abort(request: Request, _: bool = AdminDep):
    from backend.service.pipeline_worker import trigger_abort
    trigger_abort()
    return {"status": "aborted", "message": "Emergency abort signal issued"}


@app.post(
    "/api/v1/admin/pause",
    tags=["Admin Control"],
    summary="Pause or resume scheduler",
)
async def admin_pause(pause: bool, request: Request, _: bool = AdminDep):
    from backend.service.scheduler_daemon import scheduler_instance
    if pause:
        scheduler_instance.pause()
    else:
        scheduler_instance.resume()
    return {"status": "paused" if pause else "resumed"}


@app.post(
    "/api/v1/admin/backup-db",
    tags=["Admin Control"],
    summary="Manual database backup",
)
async def admin_backup_db(request: Request, _: bool = AdminDep):
    import subprocess
    try:
        result = subprocess.run(
            ["powershell", "-File", "windows/backup_database.ps1"],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode == 0:
            return {"status": "success", "message": "Database backup completed"}
        return {"status": "failed", "error": result.stderr}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


# ── WebSocket: Admin Logs ──────────────────────────────────────────────────────

class AdminWSManager:
    MAX_CONNECTIONS = int(os.getenv("MAX_WS_CONNECTIONS", "50"))

    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> bool:
        if len(self.connections) >= self.MAX_CONNECTIONS:
            await ws.close(code=1013)
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


admin_ws_manager = AdminWSManager()


@app.websocket("/ws/admin/logs")
async def ws_admin_logs(websocket: WebSocket, token: Optional[str] = Query(None)):
    # Authenticate via query token for WebSocket
    if not (token and JWT_SECRET and token == JWT_SECRET):
        await websocket.close(code=1008)
        return
    if not await admin_ws_manager.connect(websocket):
        return
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        admin_ws_manager.disconnect(websocket)


@app.on_event("startup")
async def startup():
    try:
        await get_pool()
        log.info("Admin API database pool established")
    except Exception as e:
        log.warning("Admin API DB pool deferred: %s", e)


@app.on_event("shutdown")
async def shutdown():
    global _pool
    if _pool:
        await _pool.close()


__all__ = ["app", "admin_ws_manager"]

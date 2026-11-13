"""Health, readiness, metrics and visitor routes."""

from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from backend.api.limits import RATE_LIMIT_PUBLIC, limiter
from backend.api.observability import (
    CONTENT_TYPE_LATEST,
    _PROMETHEUS_AVAILABLE,
    generate_latest,
    refresh_runtime_gauges,
)
from backend.api.runtime import (
    PublicDep,
    _file_read_visits,
    _file_record_visit,
    _load_pipeline_state,
    get_pool,
    log,
)

router = APIRouter()


async def _readiness_snapshot() -> tuple[int, dict]:
    """Return the shared readiness status and HTTP code for probe endpoints.

    Readiness means PostgreSQL is reachable *and* the latest forecast cycle
    completed. Returning 503 matters: proxies and orchestrators only stop
    routing traffic when the status code is non-2xx.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    pool = await get_pool()
    if pool is None:
        return 503, {
            "status": "not_ready",
            "service": "hydrocast-backend",
            "database": "unreachable",
            "reason": "PostgreSQL pool unavailable",
            "timestamp": timestamp,
        }
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
            last_cycle = await conn.fetchrow("""
                SELECT status, start_time
                FROM simulation_runs
                ORDER BY start_time DESC LIMIT 1
            """)
    except Exception as e:
        log.warning("Readiness check failed: %s", e)
        return 503, {
            "status": "not_ready",
            "service": "hydrocast-backend",
            "database": "unreachable",
            "reason": f"Database query failed: {e}",
            "timestamp": timestamp,
        }

    ready = bool(last_cycle) and str(last_cycle["status"] or "") in ("completed", "COMPLETED")
    if not ready:
        return 503, {
            "status": "not_ready",
            "service": "hydrocast-backend",
            "database": "connected",
            "reason": "No completed forecast cycle found",
            "last_cycle": dict(last_cycle) if last_cycle else None,
            "timestamp": timestamp,
        }

    return 200, {
        "status": "ready",
        "service": "hydrocast-backend",
        "database": "connected",
        "version": "1.2.0",
        "last_cycle": dict(last_cycle),
        "timestamp": timestamp,
    }


@router.get(
    "/healthz/live",
    tags=["Health & Probes"],
    summary="Kubernetes/container liveness probe",
)
async def liveness_probe():
    """Liveness probe: returns 200 OK if the worker process is responsive."""
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get(
    "/healthz/ready",
    tags=["Health & Probes"],
    summary="Kubernetes/container readiness probe",
)
async def readiness_probe():
    """Readiness probe: PostgreSQL connectivity plus latest cycle status."""
    status_code, payload = await _readiness_snapshot()
    return JSONResponse(status_code=status_code, content=payload)


@router.get(
    "/api/v1/health",
    tags=["Health & Probes"],
    summary="Liveness probe",
    response_description="Service identity, version, and current UTC time.",
)
@router.get(
    "/health",
    tags=["Health & Probes"],
    summary="Liveness probe alias",
)
async def health_check():
    """Liveness probe for Docker healthchecks and monitoring.

    The only endpoint that requires no credential. It touches no database and no
    external service, so a `200` here means *the process is up* â€” not that the
    forecast pipeline is healthy. Use `/api/v1/status` for pipeline state.
    """
    return {
        "status": "healthy",
        "service": "hydrocast-backend",
        "version": "1.2.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/metrics",
    tags=["Observability"],
    summary="Prometheus metrics endpoint",
    response_description="Prometheus-formatted metrics for scraping.",
)
async def metrics():
    """Prometheus metrics endpoint.

    Returns Prometheus text-format metrics for request count, duration,
    in-progress gauge, DB connection status, cycle status, and alert level.
    Scrape this endpoint from Prometheus.
    """
    if not _PROMETHEUS_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={"error": "prometheus_client not installed"},
        )
    try:
        await refresh_runtime_gauges()
    except Exception:
        # Metrics enrichment is best-effort; scraping must remain available.
        pass
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@router.get(
    "/api/v1/accuracy",
    tags=["Runoff"],
    summary="Model Accuracy & Validation Metrics",
)
async def accuracy_metrics(request: Request, run_id: Optional[str] = None):
    """Return forecast accuracy metrics for a run."""
    from backend.hydrology import runs_tracker

    if run_id:
        run = runs_tracker.get_computation_run(run_id)
    else:
        runs = runs_tracker.list_computation_runs(limit=1)
        run = runs_tracker.get_computation_run(runs[0]["cycle_id"]) if runs else None

    if not run:
        raise HTTPException(
            status_code=404,
            detail="No computation runs available for validation",
        )

    validation = run.get("validation") or {}
    if not validation.get("metrics"):
        from backend.validation.validation_metrics import evaluate_forecast_accuracy

        validation = evaluate_forecast_accuracy(run)

    return {
        "cycle_id": run.get("cycle_id"),
        "validation": validation,
    }


@router.get(
    "/api/v1/ready",
    tags=["Health & Probes"],
    summary="Readiness probe",
    response_description="Whether the service is ready to serve forecast data (database + pipeline reachable).",
)
async def readiness_check():
    """Readiness probe for container orchestration.

    Unlike ``/api/v1/health`` (liveness), this touches the database and
    pipeline state. Returns ``200`` only when PostgreSQL is reachable and a
    forecast cycle has completed successfully; otherwise returns ``503`` so
    load balancers stop sending traffic until the system recovers.
    """
    status_code, payload = await _readiness_snapshot()
    return JSONResponse(status_code=status_code, content=payload)


@router.get(
    "/api/v1/db-health",
    dependencies=[PublicDep],
    tags=["Health & Probes"],
    summary="PostgreSQL database health and table statistics",
    response_description="Database connection stats, tablespace size, and per-table row counts.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def db_health(request: Request):
    """Real PostgreSQL health metrics: connection latency, tablespace size,
    active connections, and row counts for all hydrological tables."""
    import time as _t

    pool = await get_pool()
    if pool is None:
        return {
            "ok": False,
            "error": "PostgreSQL pool unavailable",
            "tables": {},
            "tablespace_mb": None,
            "active_connections": None,
            "latency_ms": None,
        }
    t0 = _t.monotonic()
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
            latency_ms = round((_t.monotonic() - t0) * 1000, 1)
            db_size = await conn.fetchval("SELECT pg_database_size(current_database())")
            tablespace_mb = round(db_size / (1024 * 1024), 1) if db_size else None
            active = await conn.fetchval(
                "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
            )
            rows = await conn.fetch("""
                SELECT relname AS table_name,
                       n_live_tup AS row_count
                FROM pg_stat_user_tables
                ORDER BY n_live_tup DESC
            """)
            tables = {r["table_name"]: r["row_count"] for r in rows}
        return {
            "ok": True,
            "latency_ms": latency_ms,
            "tablespace_mb": tablespace_mb,
            "active_connections": active,
            "tables": tables,
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "tables": {},
            "tablespace_mb": None,
            "active_connections": None,
            "latency_ms": None,
        }


@router.get(
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
                active_alerts = await conn.fetchval(
                    "SELECT COUNT(*) FROM alert_events WHERE status='active'"
                )
                pipeline_ok = await conn.fetchval("""
                    SELECT (COUNT(*) >= 12 AND COUNT(*) FILTER (WHERE status <> 'success') = 0)
                    FROM pipeline_step_log
                    WHERE cycle_id=(SELECT run_id FROM simulation_runs ORDER BY start_time DESC LIMIT 1)
                """)
            return {
                "system": "operational",
                "last_cycle": dict(last_cycle) if last_cycle else None,
                "active_alerts": active_alerts or 0,
                "pipeline_ok": bool(pipeline_ok),
                "server_time": datetime.now(timezone.utc).isoformat(),
            }
    except Exception as e:
        log.warning("Status query fallback: %s", e)

    state = _load_pipeline_state()
    if state:
        status_info = state.get("status", {})
        if not isinstance(status_info, dict):
            status_info = {}
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


@router.post(
    "/api/v1/visits/record",
    dependencies=[PublicDep],
    tags=["System"],
    summary="Record a unique visit",
    response_description="Unique-visitor counts for today and for all time.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def record_visit(request: Request):
    """Records a unique visit and returns today's and total visitor counts.

    The client IP is SHA-256 hashed before it touches the database â€” the raw
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
                ip_hash,
            )
            if not exists:
                await conn.execute(
                    "INSERT INTO site_visitor_ips (ip_hash, visit_date) VALUES ($1, CURRENT_DATE)",
                    ip_hash,
                )
                await conn.execute("""
                    INSERT INTO site_visits (visit_date, visit_count)
                    VALUES (CURRENT_DATE, 1)
                    ON CONFLICT (visit_date) DO UPDATE SET visit_count = site_visits.visit_count + 1
                """)
            daily = await conn.fetchval(
                "SELECT visit_count FROM site_visits WHERE visit_date=CURRENT_DATE"
            )
            total = await conn.fetchval("SELECT SUM(visit_count) FROM site_visits")
        return {"daily": daily or 0, "total": total or 0}
    except Exception as e:
        log.warning("Visit recording fallback: %s", e)
        counts = _file_record_visit(ip_hash)
        return {**counts, "source": "file"}


@router.get(
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


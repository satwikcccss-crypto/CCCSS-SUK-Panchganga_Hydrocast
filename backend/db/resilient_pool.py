"""
backend/db/resilient_pool.py
============================
Enterprise resilient database pool and offline staging buffer for HydroCast Windows Server.

Features:
- Thread-safe connection pooling for PostgreSQL 16 on Windows.
- Automatic reconnection with exponential backoff on transient drops.
- Disk-backed staging buffer (data/staging/pending_commits/): if PostgreSQL
  is restarting or undergoing maintenance, writes are safely queued to disk
  as structured JSON and replayed atomically upon reconnection.
- Zero-loss guarantee for real-time forecast cycles and telemetry.
- GRACEFUL DEGRADATION: When PostgreSQL is not installed/unavailable, the
  pool returns None and all API endpoints degrade to disk-backed staging
  so the system still starts and serves stub responses.
"""

import json
import logging
import os
import re
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STAGING_DIR = PROJECT_ROOT / "data" / "staging" / "pending_commits"
# An in-flight replay owns its .processing file. Only reclaim files older than
# this threshold, which indicates the owning worker crashed mid-replay.
STAGING_STALE_SECONDS = int(os.getenv("HYDROCAST_STAGING_STALE_SECONDS", "900"))
STAGING_DIR.mkdir(parents=True, exist_ok=True)

_POOL_LOCK = threading.Lock()
_POOL: Optional[pool.ThreadedConnectionPool] = None
_POOL_UNAVAILABLE = False  # Set True once we know PostgreSQL can't be reached


def get_default_db_url() -> Optional[str]:
    """Retrieve normalized PostgreSQL database URL.

    Fails closed: returns None when neither DATABASE_URL nor
    LOCAL_DATABASE_URL is set. No hardcoded credentials are ever used.
    """
    url = os.getenv("DATABASE_URL") or os.getenv("LOCAL_DATABASE_URL")
    if not url:
        return None
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def init_pool(
    minconn: int = 2,
    maxconn: int = 15,
    db_url: Optional[str] = None,
) -> Optional[pool.ThreadedConnectionPool]:
    """Initialize the global thread-safe connection pool.

    Returns None if PostgreSQL is unavailable (graceful degradation).
    """
    global _POOL, _POOL_UNAVAILABLE
    with _POOL_LOCK:
        if _POOL is not None and not _POOL.closed:
            return _POOL

        target_url = db_url or get_default_db_url()
        if target_url is None:
            log.warning(
                "No DATABASE_URL or LOCAL_DATABASE_URL configured. "
                "PostgreSQL pool not initialized; degrading to disk-backed staging."
            )
            _POOL_UNAVAILABLE = True
            return None
        log.info("Initializing HydroCast resilient PostgreSQL connection pool...")
        try:
            _POOL = pool.ThreadedConnectionPool(
                minconn=minconn,
                maxconn=maxconn,
                dsn=target_url,
                connect_timeout=3,  # short timeout for fast fail
            )
            log.info("PostgreSQL pool established (min=%d, max=%d)", minconn, maxconn)
            return _POOL
        except Exception as exc:
            _POOL_UNAVAILABLE = True
            log.warning(
                "PostgreSQL unavailable (%s). System will degrade to disk-backed staging. "
                "Install PostgreSQL 16 on the university server for full persistence.",
                exc,
            )
            return None


def close_pool() -> None:
    """Gracefully close all pooled connections."""
    global _POOL
    with _POOL_LOCK:
        if _POOL is not None and not _POOL.closed:
            _POOL.closeall()
            _POOL = None
            log.info("PostgreSQL connection pool closed.")


def check_db_health(db_url: Optional[str] = None, timeout: int = 3) -> Dict[str, Any]:
    """Check connectivity and latency to PostgreSQL.

    Returns "unreachable" (not an exception) when PostgreSQL is not installed.
    """
    target_url = db_url or get_default_db_url()
    if target_url is None:
        return {
            "status": "unconfigured",
            "latency_ms": None,
            "error": "DATABASE_URL / LOCAL_DATABASE_URL not set",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    t0 = time.perf_counter()
    try:
        conn = psycopg2.connect(target_url, connect_timeout=timeout)
        with conn.cursor() as cur:
            cur.execute("SELECT version(), current_database(), pg_is_in_recovery();")
            row = cur.fetchone()
        conn.close()
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "status": "healthy",
            "latency_ms": elapsed_ms,
            "version": row[0].split(",")[0] if row else "unknown",
            "database": row[1] if row else "unknown",
            "is_recovery": row[2] if row else False,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "status": "unreachable",
            "latency_ms": elapsed_ms,
            "error": str(exc),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }


@contextmanager
def get_resilient_connection(max_retries: int = 2, retry_delay: float = 0.5):
    """
    Context manager providing a pooled PostgreSQL connection.

    Yields None when PostgreSQL is unavailable (graceful degradation).
    Callers must check `conn is not None` before using it.
    """
    global _POOL, _POOL_UNAVAILABLE
    conn = None
    last_err = None

    # Reset the circuit-breaker flag so each call retries if PostgreSQL
    # has come back online since the last failure.
    _POOL_UNAVAILABLE = False

    for attempt in range(1, max_retries + 1):
        try:
            if _POOL is None or _POOL.closed:
                _POOL = init_pool()
                if _POOL is None:
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                        retry_delay *= 2.0
                        continue
                    yield None
                    return
            conn = _POOL.getconn()
            if conn.closed != 0:
                _POOL.putconn(conn, close=True)
                conn = _POOL.getconn()
            break
        except Exception as exc:
            last_err = exc
            log.warning(
                "DB connection attempt %d/%d failed: %s. Retrying in %.1fs...",
                attempt,
                max_retries,
                exc,
                retry_delay,
            )
            time.sleep(retry_delay)
            retry_delay *= 2.0

    if conn is None:
        _POOL_UNAVAILABLE = True
        log.warning(
            "PostgreSQL unavailable after %d attempts. Yielding None (graceful degradation).",
            max_retries,
        )
        yield None
        return

    try:
        yield conn
    except Exception:
        if not conn.closed:
            conn.rollback()
        raise
    finally:
        if _POOL is not None and not _POOL.closed and conn is not None:
            _POOL.putconn(conn)


# ── Offline Staging Buffer ───────────────────────────────────────────────────

def stage_transaction(
    table: str,
    operation: str,
    records: List[Dict[str, Any]],
    cycle_id: Optional[str] = None,
    error_reason: str = "",
) -> Path:
    """
    Persist records to disk when the database is temporarily unreachable.
    Guarantees no data loss during Windows Server maintenance or DB restarts.
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    fname = f"staged_{cycle_id or 'unknown'}_{table}_{ts}.json"
    file_path = STAGING_DIR / fname

    payload = {
        "table": table,
        "operation": operation,
        "cycle_id": cycle_id,
        "records": records,
        "error_reason": error_reason,
        "staged_at": datetime.now(timezone.utc).isoformat(),
    }

    tmp_path = file_path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, default=str, indent=2)
    tmp_path.replace(file_path)

    log.warning(
        "DB write failed (%s). Staged %d records for table '%s' to %s",
        error_reason,
        len(records),
        table,
        file_path.name,
    )
    return file_path


ALLOWED_STAGING_TABLES = frozenset({
    "simulation_runs",
    "bridge_stage_forecast",
    "hydrograph_results",
    "rainfall_station_data",
    "pipeline_step_log",
    "alert_events",
    "site_visits",
    "subbasin_rainfall_ts",
    "station_selection_log",
    "peak_discharge_events",
    "forecast_validation_metrics",
    "wrd_field_benchmarks",
    "test_metrics",
})

_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def replay_staged_transactions(conn=None) -> Dict[str, int]:
    """
    Replay all pending disk-staged transactions once the database is back online.
    Returns summary of replayed vs failed files.
    """
    # 1. Recover orphaned .processing files from a previous crashed run.
    # Never steal a file that another worker may still be replaying.
    cutoff = time.time() - STAGING_STALE_SECONDS
    for proc_file in STAGING_DIR.glob("staged_*.processing"):
        orig_name = proc_file.with_suffix("")
        if orig_name.exists():
            continue
        try:
            if proc_file.stat().st_mtime > cutoff:
                continue
            proc_file.rename(orig_name)
        except OSError:
            pass

    staged_files = sorted(STAGING_DIR.glob("staged_*.json"))
    if not staged_files:
        return {"replayed": 0, "failed": 0, "pending": 0}

    log.info("Found %d disk-staged transaction files. Replaying to PostgreSQL...", len(staged_files))
    replayed = 0
    failed = 0

    def _execute_file(active_conn, file_path: Path) -> Optional[bool]:
        # Atomic rename to prevent race condition across concurrent worker/admin replays
        proc_path = file_path.with_suffix(".json.processing")
        try:
            file_path.rename(proc_path)
        except (FileNotFoundError, OSError):
            # Another process already picked this file up.
            return None

        try:
            with open(proc_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            table = data.get("table")
            records = data.get("records", [])
            if not table or not records:
                proc_path.unlink(missing_ok=True)
                return True

            if table not in ALLOWED_STAGING_TABLES:
                log.error(
                    "Security check failed: table '%s' in staged file %s not in ALLOWED_STAGING_TABLES whitelist",
                    table,
                    proc_path.name,
                )
                raise ValueError(f"Table '{table}' is not permitted for replay")

            with active_conn.cursor() as cur:
                for item in records:
                    cols = list(item.keys())
                    for col in cols:
                        if not _IDENTIFIER_RE.match(col):
                            log.error(
                                "Security check failed: invalid column identifier '%s' in staged file %s",
                                col,
                                proc_path.name,
                            )
                            raise ValueError(f"Column identifier '{col}' is invalid")

                    vals = [item[c] for c in cols]
                    query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT DO NOTHING").format(
                        sql.Identifier(table),
                        sql.SQL(", ").join(map(sql.Identifier, cols)),
                        sql.SQL(", ").join(sql.Placeholder() * len(cols)),
                    )
                    cur.execute(query, vals)
            active_conn.commit()
            proc_path.unlink(missing_ok=True)
            return True
        except Exception:
            # Crucial: Roll back PostgreSQL transaction so connection is not left in InFailedSqlTransaction
            try:
                if hasattr(active_conn, "rollback"):
                    active_conn.rollback()
            except Exception:
                pass
            # Restore file so it can be investigated or retried
            try:
                if proc_path.exists() and not file_path.exists():
                    proc_path.rename(file_path)
            except Exception:
                pass
            raise

    if conn is not None:
        for f in staged_files:
            try:
                result = _execute_file(conn, f)
                if result is True:
                    replayed += 1
            except Exception as err:
                log.error("Failed to replay staged file %s: %s", f.name, err)
                failed += 1
    else:
        try:
            with get_resilient_connection() as active_conn:
                for f in staged_files:
                    try:
                        result = _execute_file(active_conn, f)
                        if result is True:
                            replayed += 1
                    except Exception as err:
                        log.error("Failed to replay staged file %s: %s", f.name, err)
                        failed += 1
        except Exception as pool_err:
            log.error("Cannot replay staged files, DB still unreachable: %s", pool_err)
            return {"replayed": 0, "failed": 0, "pending": len(staged_files)}

    log.info("Replay finished: %d succeeded, %d failed", replayed, failed)
    return {"replayed": replayed, "failed": failed, "pending": len(list(STAGING_DIR.glob("staged_*.json")))}

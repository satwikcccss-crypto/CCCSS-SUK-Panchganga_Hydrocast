"""SQL helpers for pipeline step and cycle lifecycle state."""
from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Optional

from backend.db.resilient_pool import get_resilient_connection

log = logging.getLogger(__name__)

def get_conn():
    """Return a pooled PostgreSQL connection (mockable in tests)."""
    return get_resilient_connection()

def step_start(conn, cycle_id: str, step_number: int, step_name: str) -> None:
    """Mark a pipeline step as RUNNING in pipeline_step_log."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO pipeline_step_log
                (cycle_id, step_number, step_name, status, start_time, end_time)
            VALUES
                (%s, %s, %s, 'RUNNING', NOW(), NOW())
            ON CONFLICT (cycle_id, step_number) DO UPDATE SET status='RUNNING'
        """, (cycle_id, step_number, step_name))
    conn.commit()

def step_done(conn, cycle_id: str, step_number: int, details: Optional[Dict[str, Any]] = None) -> None:
    """Mark a pipeline step as success with details JSON."""
    details_json = json.dumps(details) if details else None
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE pipeline_step_log
            SET status='success', details_json=%s, end_time=NOW()
            WHERE cycle_id=%s AND step_number=%s
        """, (details_json, cycle_id, step_number))
    conn.commit()

def step_fail(conn, cycle_id: str, step_number: int, error: str) -> None:
    """Mark a pipeline step as failed and flag the run as failed."""
    err = (error or "")[:2000]
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE pipeline_step_log
            SET status='failed', error_message=%s, end_time=NOW()
            WHERE cycle_id=%s AND step_number=%s
        """, (err, cycle_id, step_number))
        cur.execute("""
            UPDATE simulation_runs
            SET status='failed', end_time=NOW()
            WHERE run_id=%s
        """, (cycle_id,))
    conn.commit()

def create_cycle(conn, cycle_id: str, run_dt: datetime) -> None:
    """Insert a new simulation run row."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO simulation_runs
                (run_id, cycle_date, cycle_time, start_time, status)
            VALUES
                (%s, %s, %s, %s, 'RUNNING')
        """, (cycle_id, run_dt.date(), f"{run_dt.hour:02d}z", run_dt))
    conn.commit()

def mark_complete(conn, cycle_id: str) -> None:
    """Mark a simulation run as completed."""
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE simulation_runs
            SET status='completed', end_time=NOW()
            WHERE run_id=%s
        """, (cycle_id,))
    conn.commit()

@contextmanager
def timed_step(conn, cycle_id: str, step_number: int, step_name: str):
    """Context manager: marks step RUNNING on enter, FAILED on exception."""
    step_start(conn, cycle_id, step_number, step_name)
    try:
        yield
    except Exception as exc:
        step_fail(conn, cycle_id, step_number, str(exc))
        raise

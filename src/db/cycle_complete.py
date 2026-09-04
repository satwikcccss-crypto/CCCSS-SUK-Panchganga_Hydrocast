"""
src/db/cycle_complete.py — CLI shim called from GitHub Actions / Orchestrator.
=============================================================================
Updates simulation_runs table with run completion status and timestamp.
"""

import argparse
from src.db.connection import get_db_connection


def mark_cycle_complete(cycle_id: str, status: str = "completed", db_url: str = None):
    db_url = db_url or os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is required")
    conn = get_db_connection(db_url)
    if not conn:
        raise ConnectionError("Unable to establish database connection")
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE simulation_runs SET status=%s, end_time=NOW() WHERE run_id=%s",
            (status, cycle_id),
        )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Update simulation run completion status")
    ap.add_argument("--cycle_id", required=True, help="Forecast cycle identifier")
    ap.add_argument("--status", default="completed", help="Run status ('completed', 'failed')")
    args = ap.parse_args()
    mark_cycle_complete(args.cycle_id, args.status)

"""src/api/notifier.py — broadcasts cycle completion to WebSocket clients."""
import os
import logging
import requests

log = logging.getLogger(__name__)

API_BASE     = os.getenv("API_BASE_URL", "http://localhost:8000")
INTERNAL_KEY = os.getenv("INTERNAL_KEY", "internal_secret")


def broadcast_cycle_complete(cycle_id: str):
    """POST to FastAPI internal endpoint which pushes to all WebSocket clients."""
    payload = {"event": "cycle_complete", "cycle_id": cycle_id}
    try:
        r = requests.post(
            f"{API_BASE}/internal/broadcast",
            json=payload,
            headers={"X-Internal-Key": INTERNAL_KEY},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        log.info("Broadcast to %d WebSocket clients", data.get("broadcast_to", 0))
    except Exception as e:
        log.warning("Broadcast failed (non-critical): %s", e)


"""src/db/cycle_complete.py — CLI shim called from GitHub Actions."""
import argparse
import os
import psycopg2

DB_URL = os.getenv("DATABASE_URL")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycle_id", required=True)
    ap.add_argument("--status", default="completed")
    args = ap.parse_args()
    conn = psycopg2.connect(DB_URL)
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE simulation_runs SET status=%s, end_time=NOW() WHERE run_id=%s",
            (args.status, args.cycle_id),
        )
    conn.commit()
    conn.close()

"""
src/api/notifier.py — Broadcasts cycle completion to WebSocket clients.
======================================================================
Notifies the running FastAPI instance to push newly computed hydrologic states
to connected Next.js dashboard clients over WebSockets.
"""

import logging
import os
import requests

log = logging.getLogger(__name__)

API_BASE     = os.getenv("API_BASE_URL", "http://localhost:8000")
INTERNAL_KEY = os.getenv("INTERNAL_KEY", "internal_secret")


def broadcast_cycle_complete(cycle_id: str) -> None:
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

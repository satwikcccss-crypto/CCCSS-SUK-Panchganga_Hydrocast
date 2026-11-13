"""Shared API runtime: JSON fallbacks, visits, WebSocket manager, dependencies."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, WebSocket

from backend.api.keys import verify_public_key

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

async def get_pool():
    """Delegate to the canonical pool factory in main (mockable in tests)."""
    from backend.api import main

    return await main.get_pool()

def api_key() -> str:
    from backend.api import main

    return main.API_KEY or ""

def require_api_key() -> bool:
    from backend.api import main

    return bool(main.REQUIRE_API_KEY)

def _load_pipeline_state() -> Optional[dict]:
    """Load the latest pipeline state JSON for DB-offline fallback."""
    from pathlib import Path
    state_file = Path(__file__).resolve().parents[2] / "data" / "openmeteo_dss" / "latest_pipeline_state.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning("Could not parse latest_pipeline_state.json: %s", exc)
    return None

_VISIT_LEDGER_FILE = PROJECT_ROOT / "data" / "visit_ledger.json"
_visit_ledger_lock = asyncio.Lock()

def _load_visit_ledger() -> dict:
    """Load file-based visitor ledger for DB-offline fallback."""
    try:
        if _VISIT_LEDGER_FILE.exists():
            data = json.loads(_VISIT_LEDGER_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "days" in data:
                return data
    except Exception as exc:
        log.warning("Could not load visit ledger: %s", exc)
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
    if require_api_key():
        supplied = x_api_key or request.query_params.get("key") or ""
        if not verify_public_key(supplied, api_key()):
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key (use X-API-Key header or ?key=)",
            )
    return True

PublicDep = Depends(verify_public_or_key)

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
        if isinstance(data, dict):
            data.setdefault("type", "NEW_CYCLE_READY")
            data.setdefault("event", "NEW_CYCLE_READY")
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

def _jsonify(rows) -> list[dict]:
    return [dict(r) for r in rows]

def _row_get(row, key: str, default=None):
    """Read a column from a dict row or an asyncpg Record."""
    try:
        return row[key]
    except (KeyError, TypeError):
        return default

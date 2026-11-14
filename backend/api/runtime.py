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


# ── Conditional responses / field filtering ──────────────────────────────────

import hashlib
from fastapi.responses import JSONResponse, Response


def compute_etag(payload) -> str:
    """Return a weak ETag for a JSON-serializable payload."""
    try:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    except Exception:
        body = repr(payload)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:32]
    return f'W/"{digest}"'


def etag_matches(request: Request, etag: str) -> bool:
    inm = (request.headers.get("if-none-match") or "").strip()
    if not inm:
        return False
    if inm == "*":
        return True
    # Support multiple ETags in If-None-Match
    candidates = [p.strip() for p in inm.split(",") if p.strip()]
    return etag in candidates


def maybe_not_modified(request: Request, payload, cache_control: str = "no-cache") -> Response | None:
    """Return 304 Response when If-None-Match matches payload ETag, else None."""
    etag = compute_etag(payload)
    if etag_matches(request, etag):
        return Response(
            status_code=304,
            headers={"ETag": etag, "Cache-Control": cache_control},
        )
    return None


def json_with_etag(request: Request, payload, cache_control: str = "no-cache", status_code: int = 200) -> Response:
    """Return JSON with ETag and conditional 304 support."""
    etag = compute_etag(payload)
    not_modified = maybe_not_modified(request, payload, cache_control=cache_control)
    if not_modified is not None:
        return not_modified
    try:
        from fastapi.encoders import jsonable_encoder
        content = jsonable_encoder(payload)
    except Exception:
        content = json.loads(json.dumps(payload, default=str))
    resp = JSONResponse(content=content, status_code=status_code)
    resp.headers["ETag"] = etag
    resp.headers["Cache-Control"] = cache_control
    return resp


def filter_fields(payload, fields_param: str | None):
    """Filter response payload by comma-separated fields/aliases.

    Backward-compatible: returns original payload when fields_param is empty.
    Supports top-level keys and a small alias set for runoff summary widgets.
    """
    if not fields_param or not isinstance(payload, dict):
        return payload
    requested = [f.strip() for f in str(fields_param).split(",") if f.strip()]
    if not requested:
        return payload

    def _pick(path: str, obj):
        cur = obj
        for part in path.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return None
            cur = cur[part]
        return cur

    out = {}
    for key in requested:
        k = key.lower()
        # Direct top-level key
        if key in payload:
            out[key] = payload[key]
            continue
        # Common aliases
        if k in ("peak_q", "peak_discharge_m3s", "peak_discharge"):
            v = _pick("summary.peak_discharge_m3s", payload)
            if v is None:
                v = _pick("outlet.peak_discharge_m3s", payload)
            out["peak_q"] = v
        elif k in ("stage_m", "current_stage_m", "stages"):
            bridges = payload.get("bridges") or []
            stages = []
            for b in bridges if isinstance(bridges, list) else []:
                if not isinstance(b, dict):
                    continue
                stages.append({
                    "site_id": b.get("site_id"),
                    "site_name": b.get("site_name"),
                    "current_stage_m": b.get("current_stage_m", b.get("stage_m")),
                    "peak_stage_m": b.get("peak_stage_m"),
                    "alert_level": b.get("alert_level"),
                })
            out["stage_m"] = stages
        elif k in ("alert_level", "alert"):
            v = _pick("summary.alert_level", payload)
            if v is None:
                v = _pick("outlet.alert_level", payload)
            out["alert_level"] = v
        elif k in ("lead_hours", "lead_hours_to_peak"):
            v = _pick("summary.lead_hours_to_peak", payload)
            if v is None:
                v = _pick("outlet.lead_hours_to_peak", payload)
            out["lead_hours_to_peak"] = v
        elif k in ("total_volume_mcm", "volume_mcm"):
            v = _pick("summary.total_volume_mcm", payload)
            if v is None:
                v = _pick("outlet.total_volume_mcm", payload)
            out["total_volume_mcm"] = v
        elif k in ("cycle_id", "run_id"):
            # best-effort passthrough from common locations
            for candidate in ("cycle_id", "run_id"):
                if candidate in payload:
                    out[candidate] = payload[candidate]
                    break
        else:
            # Try case-insensitive top-level match
            match = next((pk for pk in payload.keys() if str(pk).lower() == k), None)
            if match is not None:
                out[match] = payload[match]
    return out if out else payload

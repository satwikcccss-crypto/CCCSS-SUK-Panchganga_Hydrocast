"""Live sensor, WebSocket and internal broadcast routes."""
from __future__ import annotations

import hmac
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Request, WebSocket, WebSocketDisconnect

from backend.api.keys import verify_public_key
from backend.api.limits import RATE_LIMIT_PUBLIC, limiter
from backend.api.runtime import (
    PublicDep,
    api_key,
    log,
    require_api_key,
    ws_manager,
)

router = APIRouter()

@router.websocket(
    "/ws/live",
    name="live_cycle_push",
)
@router.websocket(
    "/ws/telemetry",
    name="telemetry_cycle_push",
)
async def ws_live(websocket: WebSocket):
    """Push new data to connected dashboards after each completed cycle.

    The pipeline orchestrator calls `ws_manager.broadcast()` after step 12.
    Dead connections are detected on send and reaped automatically, so a
    browser that vanishes mid-cycle does not block the remaining subscribers.

    The socket is protected by the same public API key as the REST routes
    (``X-API-Key`` header or ``?key=`` query param). Unauthenticated clients
    are rejected with a 4001 close code before the connection is accepted.
    """
    # ── WebSocket authentication ─────────────────────────────────────────
    supplied = websocket.headers.get("x-api-key") or websocket.query_params.get("key") or ""
    if require_api_key() and not verify_public_key(supplied, api_key() or ""):
        await websocket.close(code=4001)  # 4001 = custom "unauthorized"
        log.warning("WebSocket rejected: missing or invalid API key")
        return
    # ─────────────────────────────────────────────────────────────────────

    if not await ws_manager.connect(websocket):
        return
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

@router.get(
    "/api/v1/sensors/live",
    dependencies=[PublicDep],
    tags=["Sensors"],
    summary="Live readings from all IoT sensor stations",
    response_description="Current water level, voltage, and status for each station in the sensor network.",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def sensor_network_live(request: Request):
    """Fetch live telemetry from all configured ThingSpeak ultrasonic radar stations.

    Returns the current water level (meters MSL), raw distance (feet),
    sensor voltage (where available), and online status for each station:
    Shivaji Bridge (SS), Nitawade RWLS (NW), and Ichalkaranji (IK).
    """
    from backend.thingspeak.multi_station import fetch_all_stations
    stations = fetch_all_stations()
    online_count = sum(1 for s in stations if s.get("status") == "ONLINE")
    return {
        "stations": stations,
        "total": len(stations),
        "online": online_count,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

@router.get(
    "/api/v1/sensors/{station_id}",
    dependencies=[PublicDep],
    tags=["Sensors"],
    summary="Live reading from a single sensor station",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def sensor_station_live(request: Request, station_id: str):
    """Fetch live telemetry from a single station (SS, NW, or IK)."""
    from backend.thingspeak.multi_station import fetch_station
    result = fetch_station(station_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Station '{station_id}' not found. Valid: SS, NW, IK")
    return result

@router.get(
    "/api/v1/sensors/registry",
    dependencies=[PublicDep],
    tags=["Sensors"],
    summary="Sensor station metadata registry",
)
@limiter.limit(RATE_LIMIT_PUBLIC)
async def sensor_registry(request: Request):
    """Return station metadata (coordinates, datum, zero level) without fetching live data."""
    from backend.thingspeak.multi_station import get_station_registry
    return {"stations": get_station_registry()}

@router.post("/internal/broadcast", include_in_schema=False)
async def internal_broadcast(payload: dict, x_internal_key: str = Header(None)):
    """Called by orchestrator after each successful cycle. Not public."""
    _ik = os.getenv("INTERNAL_KEY", "")
    if len(_ik) < 16:
        # Fail closed: a short/empty shared secret is not an acceptable credential.
        raise HTTPException(status_code=503, detail="Internal auth not configured")
    supplied = str(x_internal_key or "")
    if not hmac.compare_digest(supplied.encode("utf-8"), _ik.encode("utf-8")):
        raise HTTPException(status_code=403, detail="Invalid internal key")
    await ws_manager.broadcast(payload)
    return {"broadcast_to": len(ws_manager.connections)}

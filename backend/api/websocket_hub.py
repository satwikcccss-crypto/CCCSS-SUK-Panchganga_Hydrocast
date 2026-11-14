"""
src/api/websocket_hub.py
========================
Real-Time WebSocket Hub for HydroCast Windows Server Operator Console.

Endpoints:
- WS /ws/admin/logs       Streaming log output from active pipeline and system daemons.
- WS /ws/admin/telemetry  Streaming CPU, RAM, Disk, DB pool and active run status (3s cadence).
"""

import asyncio
import hmac
import logging
import os
from typing import Optional, Set

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from backend.service.pipeline_worker import get_live_logs, ACTIVE_RUN_METADATA
from backend.service.scheduler_daemon import scheduler_instance
from backend.service.watchdog import get_hardware_telemetry

log = logging.getLogger(__name__)

router = APIRouter(tags=["WebSockets"])

# Active connections registries
_LOG_CLIENTS: Set[WebSocket] = set()
_TELEMETRY_CLIENTS: Set[WebSocket] = set()


def _ws_admin_authorized(token: Optional[str]) -> bool:
    """Authenticate admin WS using JWT bearer token or master API key (query param).

    The JWT must carry role == "admin" (operator). Official/viewer accounts
    holding authenticated console tokens cannot open operator WS streams;
    a rejected viewer attempt is recorded in admin_audit_log.
    """
    if not token:
        return False
    try:
        from backend.api.security import decode_access_token

        claims = decode_access_token(token)
        role = str(claims.get("role", "")).lower()
        if role == "admin":
            return True
        _log_viewer_block(claims, "/ws/admin")
        return False
    except Exception:
        api_key = os.getenv("API_KEY", "")
        return bool(api_key and hmac.compare_digest(token, api_key))


def _log_viewer_block(claims: dict, path: str) -> None:
    """Best-effort record of a blocked official action (never raises)."""
    try:
        import asyncio

        from backend.api.admin_routes.shared import record_admin_audit

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                record_admin_audit(
                    action="VIEWER_BLOCKED",
                    admin_user=str(claims.get("sub", "unknown")),
                    parameters={"path": path},
                    status="BLOCKED",
                    output={"reason": "role mismatch: viewer/govt requires admin"},
                )
            )
        except RuntimeError:
            pass
    except Exception as exc:  # pragma: no cover - audit must never mask close
        log.debug("viewer-blocked audit skipped: %s", exc)


@router.websocket("/ws/admin/logs")
async def websocket_logs_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    """
    Streams live orchestrator & system log events directly to the Operator Console.
    Requires admin JWT or master API key via `?token=`.
    """
    if not _ws_admin_authorized(token):
        await websocket.close(code=1008)
        return

    await websocket.accept()
    _LOG_CLIENTS.add(websocket)
    log.info("Operator Console connected to live log WebSocket stream.")

    try:
        # 1. Send recent history on connection
        initial_logs = get_live_logs()
        await websocket.send_json({"type": "history", "logs": initial_logs})

        last_sent_ts = initial_logs[-1]["timestamp"] if initial_logs else None

        # 2. Stream new lines as they arrive
        while True:
            await asyncio.sleep(0.5)
            new_logs = get_live_logs(since_ts=last_sent_ts)
            if new_logs:
                last_sent_ts = new_logs[-1]["timestamp"]
                await websocket.send_json({"type": "log_batch", "logs": new_logs})
    except (WebSocketDisconnect, asyncio.CancelledError):
        log.info("Operator Console disconnected from log stream.")
    except Exception as exc:
        log.debug("Log WebSocket exception: %s", exc)
    finally:
        _LOG_CLIENTS.discard(websocket)


@router.websocket("/ws/admin/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    """
    Streams live hardware telemetry, scheduler heartbeat and active pipeline state every 2 seconds.
    Requires admin JWT or master API key via `?token=`.
    """
    if not _ws_admin_authorized(token):
        await websocket.close(code=1008)
        return

    await websocket.accept()
    _TELEMETRY_CLIENTS.add(websocket)
    log.info("Operator Console connected to live telemetry WebSocket stream.")

    try:
        while True:
            hw = await asyncio.to_thread(get_hardware_telemetry)
            sch = scheduler_instance.get_status()
            active_run = dict(ACTIVE_RUN_METADATA)

            payload = {
                "type": "telemetry",
                "hardware": hw,
                "scheduler": sch,
                "active_run": active_run,
            }
            await websocket.send_json(payload)
            await asyncio.sleep(2.0)
    except (WebSocketDisconnect, asyncio.CancelledError):
        log.info("Operator Console disconnected from telemetry stream.")
    except Exception as exc:
        log.debug("Telemetry WebSocket exception: %s", exc)
    finally:
        _TELEMETRY_CLIENTS.discard(websocket)



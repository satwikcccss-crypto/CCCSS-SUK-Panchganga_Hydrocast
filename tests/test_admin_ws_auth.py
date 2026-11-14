import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from backend.api import websocket_hub


def _app():
    app = FastAPI()
    app.include_router(websocket_hub.router)
    return app


def test_admin_logs_ws_rejects_missing_token():
    client = TestClient(_app())
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/admin/logs"):
            pass
    assert exc.value.code == 1008


def test_admin_telemetry_ws_rejects_invalid_token(monkeypatch):
    monkeypatch.setenv("API_KEY", "expected-master-key-123456")
    client = TestClient(_app())
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/admin/telemetry?token=wrong-token"):
            pass
    assert exc.value.code == 1008


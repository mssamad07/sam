"""
Integration tests for FastAPI server and WebSocket IPC gateway.
"""
import json

from starlette.testclient import TestClient

from sam_core.api.server import app
from sam_core.config import settings


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert data["app_name"] == settings.app_name
    assert data["version"] == settings.version
    # Truthful reporting verification: unbuilt subsystems must NOT be reported as ready
    subsystems = data["subsystems"]
    assert subsystems["core"] == "ready"
    assert subsystems["ai_engine"] == "ready"
    assert subsystems["conversation_engine"] == "ready"
    assert subsystems["windows_automation"] == "ready"
    assert subsystems["voice_engine"] == "not_implemented"
    assert subsystems["android_client"] == "not_implemented"


def test_root_endpoint():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "operational"


def test_websocket_rpc_ping():
    client = TestClient(app)
    with client.websocket_connect(settings.ws_path) as ws:
        req = {
            "jsonrpc": "2.0",
            "method": "sam.ping",
            "params": {},
            "id": "test-ping-1",
        }
        ws.send_text(json.dumps(req))
        raw = ws.receive_text()
        resp = json.loads(raw)
        assert resp["id"] == "test-ping-1"
        assert resp["result"]["pong"] is True
        assert resp["result"]["app"] == settings.app_name


def test_websocket_rpc_status():
    client = TestClient(app)
    with client.websocket_connect(settings.ws_path) as ws:
        req = {
            "jsonrpc": "2.0",
            "method": "sam.status",
            "params": {},
            "id": "test-status-1",
        }
        ws.send_text(json.dumps(req))
        raw = ws.receive_text()
        resp = json.loads(raw)
        assert "ready" in resp["result"]["subsystems"]["ai_engine"]
        assert resp["result"]["subsystems"]["voice_engine"] == "ready"


def test_websocket_rpc_unknown_method():
    client = TestClient(app)
    with client.websocket_connect(settings.ws_path) as ws:
        req = {
            "jsonrpc": "2.0",
            "method": "sam.non_existent_command",
            "params": {},
            "id": 999,
        }
        ws.send_text(json.dumps(req))
        raw = ws.receive_text()
        resp = json.loads(raw)
        assert resp["id"] == 999
        assert resp["error"]["code"] == -32601
        assert "not found" in resp["error"]["message"].lower()


def test_websocket_rpc_malformed_json():
    client = TestClient(app)
    with client.websocket_connect(settings.ws_path) as ws:
        ws.send_text("this is completely invalid json {{{")
        raw = ws.receive_text()
        resp = json.loads(raw)
        assert resp["id"] is None
        assert resp["error"]["code"] == -32700
        assert "Invalid JSON" in resp["error"]["message"]

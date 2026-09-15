"""
Unit tests for JSON-RPC 2.0 protocol handler.
"""
import json

import pytest

from sam_core.api.rpc_handler import JsonRpcHandler


@pytest.mark.asyncio
async def test_rpc_ping():
    handler = JsonRpcHandler()
    payload = json.dumps({
        "jsonrpc": "2.0",
        "method": "sam.ping",
        "params": {},
        "id": 1,
    })

    raw_resp = await handler.handle_payload(payload)
    resp = json.loads(raw_resp)

    assert resp["id"] == 1
    assert resp["result"]["pong"] is True


@pytest.mark.asyncio
async def test_rpc_invalid_method():
    handler = JsonRpcHandler()
    payload = json.dumps({
        "jsonrpc": "2.0",
        "method": "non_existent_method",
        "id": "req-99",
    })

    raw_resp = await handler.handle_payload(payload)
    resp = json.loads(raw_resp)

    assert resp["id"] == "req-99"
    assert "error" in resp
    assert resp["error"]["code"] == -32601

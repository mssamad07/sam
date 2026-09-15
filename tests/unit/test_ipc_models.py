"""
Unit tests for JSON-RPC 2.0 IPC models and protocol parsing.
"""
import pytest

from sam_core.api.ipc_models import (
    JsonRpcErrorCode,
    JsonRpcNotification,
    JsonRpcRequest,
    JsonRpcResponse,
    parse_ipc_message,
)


def test_valid_request():
    raw = '{"jsonrpc": "2.0", "method": "sam.ping", "params": {}, "id": "req-1"}'
    msg = parse_ipc_message(raw)
    assert isinstance(msg, JsonRpcRequest)
    assert msg.id == "req-1"
    assert msg.method == "sam.ping"
    assert msg.params == {}


def test_valid_notification():
    raw = '{"jsonrpc": "2.0", "method": "sam.notify", "params": {"event": "started"}}'
    msg = parse_ipc_message(raw)
    assert isinstance(msg, JsonRpcNotification)
    assert msg.method == "sam.notify"
    assert msg.params == {"event": "started"}


def test_response_success_and_error():
    succ = JsonRpcResponse.success(req_id=1, result={"status": "ok"})
    assert succ.id == 1
    assert succ.result == {"status": "ok"}
    assert succ.error is None

    err = JsonRpcResponse.failure(req_id=2, code=JsonRpcErrorCode.METHOD_NOT_FOUND, message="Not found")
    assert err.id == 2
    assert err.result is None
    assert err.error.code == -32601
    assert err.error.message == "Not found"


def test_invalid_json():
    with pytest.raises(ValueError) as exc:
        parse_ipc_message("this is not json")
    assert "Invalid JSON" in str(exc.value)


def test_missing_jsonrpc_version():
    raw = '{"method": "sam.ping", "id": 1}'
    with pytest.raises(ValueError) as exc:
        parse_ipc_message(raw)
    assert "Invalid JSON-RPC protocol version" in str(exc.value)


def test_missing_method():
    raw = '{"jsonrpc": "2.0", "id": 1}'
    with pytest.raises(ValueError):
        parse_ipc_message(raw)


def test_response_cannot_have_both_result_and_error():
    with pytest.raises(ValueError):
        JsonRpcResponse(
            jsonrpc="2.0",
            id=1,
            result="ok",
            error={"code": -32000, "message": "error"},
        )

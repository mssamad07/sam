"""
Strongly typed JSON-RPC 2.0 IPC protocol models for Sam Core.
Supports requests, responses, errors, and notifications.
"""
import json
from enum import IntEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class JsonRpcErrorCode(IntEnum):
    """Standard JSON-RPC 2.0 error codes."""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    UNAUTHORIZED = -32001
    PERMISSION_DENIED = -32002


class JsonRpcError(BaseModel):
    """JSON-RPC 2.0 Error object."""
    code: int
    message: str
    data: Any | None = None


class JsonRpcRequest(BaseModel):
    """JSON-RPC 2.0 Request model. Requires 'id'."""
    jsonrpc: Literal["2.0"] = "2.0"
    method: str = Field(..., min_length=1, description="The name of the method to be invoked.")
    params: dict[str, Any] | None = Field(default_factory=dict, description="Method parameters.")
    id: str | int = Field(..., description="Unique client-supplied identifier.")


class JsonRpcNotification(BaseModel):
    """JSON-RPC 2.0 Notification model. Does NOT have an 'id'."""
    jsonrpc: Literal["2.0"] = "2.0"
    method: str = Field(..., min_length=1, description="The name of the event/notification.")
    params: dict[str, Any] | None = Field(default_factory=dict, description="Event parameters.")


class JsonRpcResponse(BaseModel):
    """JSON-RPC 2.0 Response model."""
    jsonrpc: Literal["2.0"] = "2.0"
    id: str | int | None = None
    result: Any | None = None
    error: JsonRpcError | None = None

    @model_validator(mode="after")
    def validate_result_xor_error(self) -> "JsonRpcResponse":
        """JSON-RPC requires either result or error, but not both."""
        if self.result is not None and self.error is not None:
            raise ValueError("Response cannot contain both 'result' and 'error'.")
        if self.result is None and self.error is None:
            raise ValueError("Response must contain either 'result' or 'error'.")
        return self

    @classmethod
    def success(cls, req_id: str | int, result: Any) -> "JsonRpcResponse":
        """Convenience constructor for success response."""
        return cls(id=req_id, result=result, error=None)

    @classmethod
    def failure(
        cls,
        req_id: str | int | None,
        code: int | JsonRpcErrorCode,
        message: str,
        data: Any | None = None,
    ) -> "JsonRpcResponse":
        """Convenience constructor for error response."""
        return cls(
            id=req_id,
            result=None,
            error=JsonRpcError(code=int(code), message=message, data=data),
        )


def parse_ipc_message(raw_text: str) -> JsonRpcRequest | JsonRpcNotification:
    """
    Parse and strictly validate an incoming JSON-RPC string.
    Raises ValueError on parse or schema validation errors.
    """
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("JSON-RPC message must be a JSON object.")

    if data.get("jsonrpc") != "2.0":
        raise ValueError("Invalid JSON-RPC protocol version. Expected '2.0'.")

    # If 'id' is present, it is a Request; otherwise a Notification
    if "id" in data:
        return JsonRpcRequest(**data)
    else:
        return JsonRpcNotification(**data)

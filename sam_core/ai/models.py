"""
Data models for LLM message history, tool calls, and provider responses.
Provider-agnostic and strongly typed.
"""
import uuid
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class MessageRole(StrEnum):
    """Roles supported in conversation history."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolCall(BaseModel):
    """Specification of a tool call emitted by an LLM."""
    call_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Tool name to execute")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Parsed arguments dictionary")


class LLMMessage(BaseModel):
    """A single message in the conversation context."""
    role: MessageRole
    content: str
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    name: str | None = None


class ProviderStatus(BaseModel):
    """Availability and health status of an LLM provider."""
    name: str
    available: bool
    configured: bool
    model: str
    message: str | None = None


class LLMResponse(BaseModel):
    """Unified response from any LLM provider."""
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: dict[str, int] = Field(default_factory=dict)
    finish_reason: str | None = None
    provider: str
    model: str

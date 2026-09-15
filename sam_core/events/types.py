"""
Typed event models for Sam's asynchronous pub-sub event bus.
"""
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    """Base event model that all system events inherit from."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: str = Field(default="system", description="Origin of the event (e.g., client, core, voice)")


class UserInputEvent(BaseEvent):
    """Fired when input arrives from user (text or transcribed speech)."""
    text: str
    channel: str = "text"  # 'voice', 'text', 'shortcut'
    client_id: str | None = None
    language_hint: str | None = None


class AssistantMessageEvent(BaseEvent):
    """Fired when assistant generates a conversational response."""
    text: str
    language: str = "en"
    client_id: str | None = None
    is_final: bool = True


class ToolInvocationRequestedEvent(BaseEvent):
    """Fired when the LLM requests a tool execution."""
    call_id: str
    tool_name: str
    arguments: dict[str, Any]
    risk_tier: str


class PermissionRequestedEvent(BaseEvent):
    """Fired when an action requires explicit user authorization."""
    token: str
    tool_name: str
    arguments: dict[str, Any]
    description: str
    expires_at: datetime


class PermissionResolvedEvent(BaseEvent):
    """Fired when user grants or denies permission."""
    token: str
    approved: bool
    reason: str | None = None


class ToolExecutedEvent(BaseEvent):
    """Fired when a tool finishes execution."""
    call_id: str
    tool_name: str
    success: bool
    result: Any
    error: str | None = None


class VoiceStateChangedEvent(BaseEvent):
    """Fired when the voice engine changes state."""
    state: str  # 'idle', 'listening', 'thinking', 'speaking'
    client_id: str | None = None


class SystemStatusEvent(BaseEvent):
    """Periodic or trigger-based health and status update."""
    status: str  # 'ready', 'busy', 'degraded', 'error'
    details: dict[str, Any] = Field(default_factory=dict)

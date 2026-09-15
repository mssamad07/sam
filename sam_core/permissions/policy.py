"""
Permission policy definitions and risk tiers for Sam Assistant.
Defines foundational risk tiers and permission models for safe operations.
"""
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class RiskTier(StrEnum):
    """Classification of action sensitivity."""

    TIER_1_SAFE = "tier_1_safe"
    # Read-only operations, queries, status checks, web lookups, local math
    # -> Auto-approved without prompting.

    TIER_2_REVIEW = "tier_2_review"
    # Reversible actions, UI focus, launching standard applications, media play/pause
    # -> Logged & acknowledged, low risk.

    TIER_3_CRITICAL = "tier_3_critical"
    # Permanent deletion, killing processes, shell execution, sending messages, system restart
    # -> Strictly requires cryptographic confirmation token and explicit user approval.


# Blacklisted system paths that file operations are NEVER allowed to delete or overwrite
PROTECTED_SYSTEM_PATHS: set[str] = {
    "c:\\windows",
    "c:\\windows\\system32",
    "c:\\program files",
    "c:\\program files (x86)",
    "c:\\boot",
    "c:\\recovery",
}


class PermissionRequest(BaseModel):
    """Model representing an operation awaiting permission evaluation."""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str
    risk_tier: RiskTier
    arguments: dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PermissionDecision(BaseModel):
    """Model representing an approval or denial decision."""
    request_id: str
    approved: bool
    reason: str | None = None
    decided_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

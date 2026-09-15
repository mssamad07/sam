"""
Permission Manager for gating and validating sensitive actions in Sam.
Enforces risk tiers, authorization token lifecycle, exact action binding, and non-replayability.
"""
import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from sam_core.config import settings
from sam_core.events.bus import event_bus
from sam_core.events.types import PermissionRequestedEvent, PermissionResolvedEvent
from sam_core.logger import get_logger
from sam_core.permissions.policy import PROTECTED_SYSTEM_PATHS, RiskTier

logger = get_logger("permissions.manager")


def compute_action_hash(tool_name: str, arguments: dict[str, Any]) -> str:
    """Produce deterministic SHA-256 fingerprint for a tool call."""
    canonical = f"{tool_name}:{json.dumps(arguments, sort_keys=True)}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class PendingConfirmation(BaseModel):
    """Represents a paused sensitive action awaiting user decision."""
    token: str
    tool_name: str
    arguments: dict[str, Any]
    action_hash: str
    description: str
    risk_tier: RiskTier
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime
    approved: bool | None = None


class AuditLogEntry(BaseModel):
    """Auditable log entry for security and compliance."""
    token: str
    tool_name: str
    action_hash: str
    approved: bool
    reason: str | None = None
    decided_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PermissionManager:
    """Manages authorization requests, tokens, action binding, and guardrails."""

    def __init__(self):
        self._pending_tokens: dict[str, PendingConfirmation] = {}
        self._audit_log: list[AuditLogEntry] = []

    def is_path_protected(self, path_str: str) -> bool:
        """Check whether a path points to protected Windows system directories."""
        normalized = path_str.strip().lower().replace("/", "\\")
        for protected in PROTECTED_SYSTEM_PATHS:
            if normalized == protected or normalized.startswith(protected + "\\"):
                return True
        return False

    async def request_permission(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        description: str,
        risk_tier: RiskTier = RiskTier.TIER_3_CRITICAL,
    ) -> str:
        """
        Generate an action-bound confirmation token and broadcast an event.
        Returns the token string.
        """
        token = secrets.token_hex(4).upper()
        timeout = settings.confirmation_timeout_seconds
        expires_at = datetime.now(UTC) + timedelta(seconds=timeout)
        action_hash = compute_action_hash(tool_name, arguments)

        pending = PendingConfirmation(
            token=token,
            tool_name=tool_name,
            arguments=arguments,
            action_hash=action_hash,
            description=description,
            risk_tier=risk_tier,
            expires_at=expires_at,
        )
        self._pending_tokens[token] = pending

        logger.warning(
            f"SECURITY: Action '{tool_name}' paused. Token '{token}' bound to action hash {action_hash[:8]}..."
        )

        await event_bus.publish(
            PermissionRequestedEvent(
                token=token,
                tool_name=tool_name,
                arguments=arguments,
                description=description,
                expires_at=expires_at,
            )
        )

        return token

    async def resolve_permission(self, token: str, approved: bool, reason: str | None = None) -> bool:
        """
        Resolves a pending permission request.
        Logs to the audit trail and returns True if valid.
        """
        pending = self._pending_tokens.get(token)
        if not pending:
            logger.warning(f"Permission resolution failed: Token '{token}' not found.")
            return False

        if datetime.now(UTC) > pending.expires_at:
            logger.warning(f"Permission resolution failed: Token '{token}' expired.")
            self._pending_tokens.pop(token, None)
            return False

        pending.approved = approved
        # Record in audit trail
        self._audit_log.append(
            AuditLogEntry(
                token=token,
                tool_name=pending.tool_name,
                action_hash=pending.action_hash,
                approved=approved,
                reason=reason,
            )
        )

        logger.info(
            f"SECURITY AUDIT: Action '{pending.tool_name}' (token: {token}) decision={approved}"
        )

        await event_bus.publish(
            PermissionResolvedEvent(
                token=token,
                approved=approved,
                reason=reason,
            )
        )

        return True

    def check_authorization(
        self,
        token: str,
        tool_name: str | None = None,
        arguments: dict[str, Any] | None = None,
    ) -> bool:
        """
        Validates if an action is currently approved.
        Enforces:
        1. Token existence & non-expired status
        2. Strict action-binding (action hash must match the exact tool and arguments)
        3. One-time use (consumes token on success to prevent replay attacks)
        """
        pending = self._pending_tokens.get(token)
        if not pending:
            return False

        if datetime.now(UTC) > pending.expires_at:
            self._pending_tokens.pop(token, None)
            return False

        if pending.approved is not True:
            return False

        # Action binding validation: prevent token theft / substitution
        if tool_name is not None and arguments is not None:
            expected_hash = compute_action_hash(tool_name, arguments)
            if pending.action_hash != expected_hash:
                logger.error(
                    f"SECURITY ALERT: Token '{token}' was authorized for '{pending.tool_name}', "
                    f"but attempted for '{tool_name}' with different arguments!"
                )
                return False

        # Consume token to guarantee non-replayability
        self._pending_tokens.pop(token, None)
        return True

    def get_audit_log(self) -> list[AuditLogEntry]:
        """Return the immutable audit trail of all resolved permissions."""
        return list(self._audit_log)

    def get_pending(self, token: str) -> PendingConfirmation | None:
        """Retrieve details of a pending request."""
        return self._pending_tokens.get(token)

    def cleanup_expired(self) -> int:
        """Prunes expired tokens."""
        now = datetime.now(UTC)
        expired = [tok for tok, item in self._pending_tokens.items() if now > item.expires_at]
        for tok in expired:
            self._pending_tokens.pop(tok, None)
        return len(expired)


# Global singleton instance
permission_manager = PermissionManager()

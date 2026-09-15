"""
Permission Manager for gating and validating sensitive actions in Sam.
Enforces risk tiers and authorization token lifecycle.
"""
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


class PendingConfirmation(BaseModel):
    """Represents a paused sensitive action awaiting user decision."""
    token: str
    tool_name: str
    arguments: dict[str, Any]
    description: str
    risk_tier: RiskTier
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime
    approved: bool | None = None


class PermissionManager:
    """Manages authorization requests, tokens, and guardrails."""

    def __init__(self):
        self._pending_tokens: dict[str, PendingConfirmation] = {}

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
        Generate a confirmation token, store the pending action, and broadcast an event.
        Returns the token string.
        """
        token = secrets.token_hex(4).upper()
        timeout = settings.confirmation_timeout_seconds
        expires_at = datetime.now(UTC) + timedelta(seconds=timeout)

        pending = PendingConfirmation(
            token=token,
            tool_name=tool_name,
            arguments=arguments,
            description=description,
            risk_tier=risk_tier,
            expires_at=expires_at,
        )
        self._pending_tokens[token] = pending

        logger.warning(
            f"SECURITY: Action '{tool_name}' paused. Token '{token}' generated. Awaiting user approval."
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
        Returns True if the token was valid and unresolved, False otherwise.
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
        logger.info(f"Permission for action '{pending.tool_name}' (token: {token}) marked approved={approved}")

        await event_bus.publish(
            PermissionResolvedEvent(
                token=token,
                approved=approved,
                reason=reason,
            )
        )

        return True

    def check_authorization(self, token: str) -> bool:
        """
        Validates if an action is currently approved. Consumes the token if approved.
        """
        pending = self._pending_tokens.get(token)
        if not pending:
            return False

        if datetime.now(UTC) > pending.expires_at:
            self._pending_tokens.pop(token, None)
            return False

        if pending.approved is True:
            # Consume token so it cannot be replayed
            self._pending_tokens.pop(token, None)
            return True

        return False

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

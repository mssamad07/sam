"""
Unit tests for permission risk tiers and validation foundation.
"""
import pytest

from sam_core.permissions.manager import PermissionManager
from sam_core.permissions.policy import (
    PermissionDecision,
    PermissionRequest,
    RiskTier,
)


def test_risk_tier_values():
    assert RiskTier.TIER_1_SAFE == "tier_1_safe"
    assert RiskTier.TIER_2_REVIEW == "tier_2_review"
    assert RiskTier.TIER_3_CRITICAL == "tier_3_critical"


def test_permission_request_model():
    req = PermissionRequest(
        tool_name="test_tool",
        risk_tier=RiskTier.TIER_3_CRITICAL,
        arguments={"param": 123},
        description="Testing action",
    )
    assert req.request_id is not None
    assert req.risk_tier == RiskTier.TIER_3_CRITICAL
    assert req.arguments == {"param": 123}


def test_permission_decision_model():
    dec = PermissionDecision(
        request_id="req-123",
        approved=True,
        reason="User accepted prompt",
    )
    assert dec.request_id == "req-123"
    assert dec.approved is True
    assert dec.reason == "User accepted prompt"


@pytest.mark.asyncio
async def test_permission_manager_token_lifecycle():
    pm = PermissionManager()
    token = await pm.request_permission(
        tool_name="sensitive_action",
        arguments={"flag": True},
        description="Critical test",
        risk_tier=RiskTier.TIER_3_CRITICAL,
    )
    assert token is not None
    assert pm.check_authorization(token) is False

    # Grant permission
    res = await pm.resolve_permission(token, approved=True)
    assert res is True
    assert pm.check_authorization(token) is True
    # Replay protection: token must be consumed
    assert pm.check_authorization(token) is False


def test_protected_system_paths_guardrail():
    pm = PermissionManager()
    assert pm.is_path_protected("C:\\Windows\\System32") is True
    assert pm.is_path_protected("C:/Program Files/app") is True
    assert pm.is_path_protected("C:\\Users\\User\\Documents") is False

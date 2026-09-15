"""
Unit tests for Phase 3 advanced permission engine: action-binding, anti-replay, and audit trails.
"""
import pytest

from sam_core.permissions.manager import PermissionManager
from sam_core.permissions.policy import RiskTier


@pytest.mark.asyncio
async def test_action_binding_security():
    """Verify that a token cannot be reused for a different action or altered arguments."""
    pm = PermissionManager()
    
    # 1. Request permission for Action A
    token = await pm.request_permission(
        tool_name="recycle_file",
        arguments={"path": "C:\\temp\\test.txt"},
        description="Recycle test file",
        risk_tier=RiskTier.TIER_3_CRITICAL,
    )

    # 2. User approves token for Action A
    await pm.resolve_permission(token=token, approved=True)

    # 3. Attacker tries to use token for Action B (different path)
    tampered_auth = pm.check_authorization(
        token=token,
        tool_name="recycle_file",
        arguments={"path": "C:\\important\\database.sqlite"},
    )
    assert tampered_auth is False, "Security breach: token approved for different arguments!"

    # 4. Attacker tries to use token for entirely different tool
    tool_tampered = pm.check_authorization(
        token=token,
        tool_name="kill_process",
        arguments={"target": "explorer.exe"},
    )
    assert tool_tampered is False, "Security breach: token approved for different tool!"


@pytest.mark.asyncio
async def test_non_replayability():
    """Verify that an authorization token is strictly single-use."""
    pm = PermissionManager()
    token = await pm.request_permission(
        tool_name="kill_process",
        arguments={"target": "calc.exe"},
        description="Kill calc",
        risk_tier=RiskTier.TIER_3_CRITICAL,
    )
    await pm.resolve_permission(token=token, approved=True)

    # First check succeeds and consumes token
    first_check = pm.check_authorization(token=token, tool_name="kill_process", arguments={"target": "calc.exe"})
    assert first_check is True

    # Second check must fail (replay attack prevented)
    second_check = pm.check_authorization(token=token, tool_name="kill_process", arguments={"target": "calc.exe"})
    assert second_check is False


@pytest.mark.asyncio
async def test_audit_trail_logging():
    pm = PermissionManager()
    token = await pm.request_permission(
        tool_name="write_file",
        arguments={"path": "test.txt"},
        description="Write test",
        risk_tier=RiskTier.TIER_2_REVIEW,
    )
    await pm.resolve_permission(token=token, approved=True, reason="User approved via modal")

    audit = pm.get_audit_log()
    assert len(audit) >= 1
    last = audit[-1]
    assert last.token == token
    assert last.tool_name == "write_file"
    assert last.approved is True
    assert last.reason == "User approved via modal"

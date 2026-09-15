"""
Unit tests for ControlledShellSkill: security blacklists, risk classification, and secret masking.
"""
import pytest

from sam_capabilities.shell.controlled_shell import ControlledShellSkill, classify_command_risk
from sam_core.permissions.policy import RiskTier


def test_command_risk_classification():
    assert classify_command_risk("dir") == RiskTier.TIER_2_REVIEW
    assert classify_command_risk("echo hello") == RiskTier.TIER_2_REVIEW
    assert classify_command_risk("git status") == RiskTier.TIER_2_REVIEW
    assert classify_command_risk("python --version") == RiskTier.TIER_2_REVIEW
    assert classify_command_risk("pip install some_package") == RiskTier.TIER_3_CRITICAL
    assert classify_command_risk("del file.txt") == RiskTier.TIER_3_CRITICAL


@pytest.mark.asyncio
async def test_hard_blocked_command_rejection():
    skill = ControlledShellSkill()
    res = await skill.execute("execute_command", {"command": "format c:"})
    assert res.success is False
    assert "SECURITY VIOLATION" in res.error

    res2 = await skill.execute("execute_command", {"command": "rmdir /s c:\\windows"})
    assert res2.success is False
    assert "SECURITY VIOLATION" in res2.error


@pytest.mark.asyncio
async def test_safe_command_execution():
    skill = ControlledShellSkill()
    res = await skill.execute("execute_command", {"command": "echo HelloFromSam"})
    assert res.success is True
    assert res.data["exit_code"] == 0
    assert "HelloFromSam" in res.data["stdout"]


@pytest.mark.asyncio
async def test_timeout_enforcement():
    skill = ControlledShellSkill()
    # Execute command with 1s timeout that takes longer
    res = await skill.execute(
        "execute_command",
        {"command": "powershell -Command Start-Sleep -Seconds 5", "timeout_seconds": 1},
    )
    assert res.success is False
    assert "timed out" in res.error.lower()

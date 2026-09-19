"""
Unit tests for MobileDeviceBridgeSkill.
"""
import pytest

from sam_capabilities.mobile.bridge import MobileDeviceBridgeSkill


@pytest.mark.asyncio
async def test_mobile_bridge_tools():
    skill = MobileDeviceBridgeSkill()
    assert skill.name == "mobile_bridge"
    tools = skill.get_tools()
    tool_names = [t.name for t in tools]
    assert "trigger_find_my_phone" in tool_names
    assert "sync_clipboard_to_phone" in tool_names
    assert "get_mobile_device_status" in tool_names

@pytest.mark.asyncio
async def test_trigger_find_my_phone():
    skill = MobileDeviceBridgeSkill()
    res = await skill.execute("trigger_find_my_phone", {})
    assert res.success is True
    assert res.data.get("status") == "alarm_dispatched"

@pytest.mark.asyncio
async def test_sync_clipboard_validation():
    skill = MobileDeviceBridgeSkill()
    res = await skill.execute("sync_clipboard_to_phone", {"text": ""})
    assert res.success is False
    assert "required" in res.error.lower()

"""
Unit tests for GUIAutomationSkill.
"""
import pytest

from sam_capabilities.windows.gui_automation import GUIAutomationSkill


@pytest.mark.asyncio
async def test_gui_automation_tools():
    skill = GUIAutomationSkill()
    assert skill.name == "gui_automation"
    tools = skill.get_tools()
    tool_names = [t.name for t in tools]
    assert "get_screen_size" in tool_names
    assert "mouse_click" in tool_names
    assert "type_text" in tool_names

@pytest.mark.asyncio
async def test_gui_get_screen_size():
    skill = GUIAutomationSkill()
    res = await skill.execute("get_screen_size", {})
    assert res.success is True
    assert "width" in res.data
    assert "height" in res.data
    assert res.data["width"] > 0
    assert res.data["height"] > 0

@pytest.mark.asyncio
async def test_gui_mouse_click_validation():
    skill = GUIAutomationSkill()
    res = await skill.execute("mouse_click", {})
    assert res.success is False
    assert "coordinates are required" in res.error.lower()

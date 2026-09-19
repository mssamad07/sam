"""
Unit tests for BrowserAutomationSkill.
"""
import pytest

from sam_capabilities.web.browser_agent import BrowserAutomationSkill


@pytest.mark.asyncio
async def test_browser_automation_skill_tools():
    skill = BrowserAutomationSkill()
    assert skill.name == "browser_automation"
    tools = skill.get_tools()
    tool_names = [t.name for t in tools]
    assert "browser_open_url" in tool_names
    assert "browser_search_youtube" in tool_names
    assert "browser_search_google" in tool_names

@pytest.mark.asyncio
async def test_browser_open_url_validation():
    skill = BrowserAutomationSkill()
    res = await skill.execute("browser_open_url", {"url": ""})
    assert res.success is False
    assert "empty" in res.error.lower()

@pytest.mark.asyncio
async def test_browser_search_youtube_validation():
    skill = BrowserAutomationSkill()
    res = await skill.execute("browser_search_youtube", {"query": ""})
    assert res.success is False
    assert "empty" in res.error.lower()

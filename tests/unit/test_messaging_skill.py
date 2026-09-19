"""
Unit tests for WhatsAppSkill.
"""
import pytest

from sam_capabilities.communication.whatsapp import WhatsAppSkill


@pytest.mark.asyncio
async def test_whatsapp_skill_tools():
    skill = WhatsAppSkill()
    assert skill.name == "whatsapp"
    tools = skill.get_tools()
    tool_names = [t.name for t in tools]
    assert "whatsapp_send_message" in tool_names
    assert "whatsapp_open" in tool_names

@pytest.mark.asyncio
async def test_whatsapp_send_validation():
    skill = WhatsAppSkill()
    res = await skill.execute("whatsapp_send_message", {"phone_number": ""})
    assert res.success is False
    assert "phone number" in res.error.lower()

    res2 = await skill.execute("whatsapp_send_message", {"phone_number": "919876543210", "message": ""})
    assert res2.success is False
    assert "message text cannot be empty" in res2.error.lower()

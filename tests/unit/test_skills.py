"""
Unit tests for Skill foundation and SkillRegistry.
"""
from typing import Any

import pytest

from sam_capabilities.base import BaseSkill, ToolDefinition, ToolResult
from sam_capabilities.registry import SkillRegistry


class DummySkill(BaseSkill):
    def __init__(self, name: str = "dummy"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return "A dummy testing skill"

    def get_tools(self) -> list[ToolDefinition]:
        return []

    async def execute(self, tool_name: str, arguments: dict[str, Any], context=None) -> ToolResult:
        return ToolResult(success=True)


def test_skill_registration_and_retrieval():
    reg = SkillRegistry()
    skill = DummySkill("test_skill")

    assert reg.count == 0
    reg.register(skill)
    assert reg.count == 1
    assert reg.has_skill("test_skill") is True
    assert reg.get_skill("test_skill") == skill


def test_duplicate_registration_protection():
    reg = SkillRegistry()
    skill1 = DummySkill("unique_skill")
    skill2 = DummySkill("unique_skill")

    reg.register(skill1)
    with pytest.raises(ValueError) as exc:
        reg.register(skill2)

    assert "already registered" in str(exc.value)


def test_list_skills():
    reg = SkillRegistry()
    s1 = DummySkill("skill_a")
    s2 = DummySkill("skill_b")
    reg.register(s1)
    reg.register(s2)

    skills = reg.list_skills()
    assert len(skills) == 2
    names = [s.name for s in skills]
    assert "skill_a" in names
    assert "skill_b" in names


def test_unregister_skill():
    reg = SkillRegistry()
    skill = DummySkill("removable")
    reg.register(skill)

    assert reg.unregister("removable") is True
    assert reg.has_skill("removable") is False
    assert reg.unregister("non_existent") is False

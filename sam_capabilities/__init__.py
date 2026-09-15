"""
Sam Capabilities and Skills System.
Provides modular tools for Windows control, file operations, web access, and shell execution.
"""
from sam_capabilities.base import BaseSkill, ToolDefinition, ToolParameter, ToolResult
from sam_capabilities.registry import SkillRegistry, skill_registry
from sam_capabilities.shell.controlled_shell import ControlledShellSkill
from sam_capabilities.web.fetcher import WebFetchSkill
from sam_capabilities.web.search import WebSearchSkill
from sam_capabilities.windows.apps import ApplicationSkill
from sam_capabilities.windows.clipboard import ClipboardSkill
from sam_capabilities.windows.files import SafeFileSkill
from sam_capabilities.windows.media import MediaControlSkill
from sam_capabilities.windows.system_info import SystemInfoSkill


def initialize_default_skills() -> None:
    """Register standard built-in skills into the global registry."""
    skills = [
        SystemInfoSkill(),
        ApplicationSkill(),
        MediaControlSkill(),
        SafeFileSkill(),
        ClipboardSkill(),
        ControlledShellSkill(),
        WebSearchSkill(),
        WebFetchSkill(),
    ]
    for skill in skills:
        if not skill_registry.has_skill(skill.name):
            skill_registry.register(skill)


__all__ = [
    "BaseSkill",
    "ToolDefinition",
    "ToolParameter",
    "ToolResult",
    "SkillRegistry",
    "skill_registry",
    "initialize_default_skills",
    "SystemInfoSkill",
    "ApplicationSkill",
    "MediaControlSkill",
    "SafeFileSkill",
    "ClipboardSkill",
    "ControlledShellSkill",
    "WebSearchSkill",
    "WebFetchSkill",
]

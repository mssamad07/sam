"""
Sam Capabilities and Skills System.
Provides modular tools for Windows control, file operations, web access, and shell execution.
"""
from sam_capabilities.base import BaseSkill, ToolDefinition, ToolParameter, ToolResult
from sam_capabilities.communication.whatsapp import WhatsAppSkill
from sam_capabilities.mobile.bridge import MobileDeviceBridgeSkill
from sam_capabilities.registry import SkillRegistry, skill_registry
from sam_capabilities.shell.controlled_shell import ControlledShellSkill
from sam_capabilities.web.browser_agent import BrowserAutomationSkill
from sam_capabilities.web.fetcher import WebFetchSkill
from sam_capabilities.web.search import WebSearchSkill
from sam_capabilities.windows.apps import ApplicationSkill
from sam_capabilities.windows.clipboard import ClipboardSkill
from sam_capabilities.windows.files import SafeFileSkill
from sam_capabilities.windows.gui_automation import GUIAutomationSkill
from sam_capabilities.windows.media import MediaControlSkill
from sam_capabilities.windows.system_info import SystemInfoSkill
from sam_memory.skill import MemorySkill
from sam_security.skill import MobileSecuritySkill
from sam_vision.skill import VisionSkill


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
        BrowserAutomationSkill(),
        GUIAutomationSkill(),
        WhatsAppSkill(),
        VisionSkill(),
        MemorySkill(),
        MobileSecuritySkill(),
        MobileDeviceBridgeSkill(),
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
    "BrowserAutomationSkill",
    "ClipboardSkill",
    "ControlledShellSkill",
    "GUIAutomationSkill",
    "MediaControlSkill",
    "MemorySkill",
    "MobileDeviceBridgeSkill",
    "MobileSecuritySkill",
    "SafeFileSkill",
    "SystemInfoSkill",
    "VisionSkill",
    "WebFetchSkill",
    "WebSearchSkill",
    "WhatsAppSkill",
]

"""
Windows OS Integration Capabilities for Sam.
"""
from sam_capabilities.windows.apps import ApplicationSkill
from sam_capabilities.windows.clipboard import ClipboardSkill
from sam_capabilities.windows.files import SafeFileSkill
from sam_capabilities.windows.media import MediaControlSkill
from sam_capabilities.windows.system_info import SystemInfoSkill

__all__ = [
    "SystemInfoSkill",
    "ApplicationSkill",
    "MediaControlSkill",
    "SafeFileSkill",
    "ClipboardSkill",
]

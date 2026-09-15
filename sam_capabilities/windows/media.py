"""
Media and Audio Control Capability for Sam.
Simulates volume adjustments, muting, and media playback controls via Win32 API.
"""
import ctypes
import sys
from typing import Any

from sam_capabilities.base import BaseSkill, ToolDefinition, ToolParameter, ToolResult
from sam_core.logger import get_logger
from sam_core.permissions.policy import RiskTier

logger = get_logger("capabilities.media")

# Virtual key codes for Windows multimedia
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002


def _send_key(vk_code: int):
    """Simulate single keypress on Windows."""
    if sys.platform != "win32":
        return
    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)


class MediaControlSkill(BaseSkill):
    """Controls volume, mute, and media playback."""

    @property
    def name(self) -> str:
        return "media_control"

    @property
    def description(self) -> str:
        return "Adjust volume, mute/unmute, and control media playback (play/pause/skip)."

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="volume_up",
                description="Increase system volume by specified steps (default: 2).",
                risk_tier=RiskTier.TIER_2_REVIEW,
                parameters=[
                    ToolParameter(name="steps", type_str="integer", description="Steps to increase", required=False, default=2)
                ],
            ),
            ToolDefinition(
                name="volume_down",
                description="Decrease system volume by specified steps (default: 2).",
                risk_tier=RiskTier.TIER_2_REVIEW,
                parameters=[
                    ToolParameter(name="steps", type_str="integer", description="Steps to decrease", required=False, default=2)
                ],
            ),
            ToolDefinition(
                name="toggle_mute",
                description="Toggle system audio mute on or off.",
                risk_tier=RiskTier.TIER_2_REVIEW,
            ),
            ToolDefinition(
                name="media_play_pause",
                description="Toggle media play/pause state for active music or video.",
                risk_tier=RiskTier.TIER_2_REVIEW,
            ),
            ToolDefinition(
                name="media_next",
                description="Skip to the next media track.",
                risk_tier=RiskTier.TIER_2_REVIEW,
            ),
            ToolDefinition(
                name="media_previous",
                description="Return to the previous media track.",
                risk_tier=RiskTier.TIER_2_REVIEW,
            ),
        ]

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ToolResult:
        if sys.platform != "win32":
            return ToolResult(success=False, error="MediaControl is only supported on Windows.")

        try:
            if tool_name == "volume_up":
                steps = int(arguments.get("steps", 2))
                for _ in range(steps):
                    _send_key(VK_VOLUME_UP)
                return ToolResult(success=True, data={"adjusted": "up", "steps": steps})

            elif tool_name == "volume_down":
                steps = int(arguments.get("steps", 2))
                for _ in range(steps):
                    _send_key(VK_VOLUME_DOWN)
                return ToolResult(success=True, data={"adjusted": "down", "steps": steps})

            elif tool_name == "toggle_mute":
                _send_key(VK_VOLUME_MUTE)
                return ToolResult(success=True, data={"toggled_mute": True})

            elif tool_name == "media_play_pause":
                _send_key(VK_MEDIA_PLAY_PAUSE)
                return ToolResult(success=True, data={"media_action": "play_pause"})

            elif tool_name == "media_next":
                _send_key(VK_MEDIA_NEXT_TRACK)
                return ToolResult(success=True, data={"media_action": "next_track"})

            elif tool_name == "media_previous":
                _send_key(VK_MEDIA_PREV_TRACK)
                return ToolResult(success=True, data={"media_action": "previous_track"})

        except Exception as exc:
            logger.error(f"Error executing media action '{tool_name}': {exc}")
            return ToolResult(success=False, error=str(exc))

        return ToolResult(success=False, error=f"Unknown tool '{tool_name}' in {self.name}")

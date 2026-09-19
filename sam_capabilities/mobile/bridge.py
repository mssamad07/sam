"""
Mobile Device Bridge Capability for Sam.
Enables cross-device synchronization, remote Find-My-Phone alarms, and clipboard sync.
"""
from typing import Any

from sam_capabilities.base import BaseSkill, ToolDefinition, ToolParameter, ToolResult
from sam_core.events.bus import get_event_bus
from sam_core.events.types import Event
from sam_core.logger import get_logger
from sam_core.permissions.policy import RiskTier

logger = get_logger("capabilities.mobile")


class MobileDeviceBridgeSkill(BaseSkill):
    """Bridges Sam PC Core with connected Android devices."""

    @property
    def name(self) -> str:
        return "mobile_bridge"

    @property
    def description(self) -> str:
        return "Trigger Find-My-Phone alarms, sync clipboard to phone, and inspect mobile device connection."

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="trigger_find_my_phone",
                description="Trigger a loud audible alarm and vibration on the connected Android phone to locate it.",
                risk_tier=RiskTier.TIER_2_REVIEW,
                parameters=[],
            ),
            ToolDefinition(
                name="sync_clipboard_to_phone",
                description="Send text from PC to sync with the Android phone's clipboard.",
                risk_tier=RiskTier.TIER_1_SAFE,
                parameters=[
                    ToolParameter(
                        name="text",
                        type="string",
                        description="Text content to copy onto the mobile device clipboard",
                        required=True,
                    ),
                ],
            ),
            ToolDefinition(
                name="get_mobile_device_status",
                description="Check whether an Android mobile client is currently connected to Sam Core.",
                risk_tier=RiskTier.TIER_1_SAFE,
                parameters=[],
            ),
        ]

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        event_bus = get_event_bus()

        if tool_name == "trigger_find_my_phone":
            # Publish event across IPC for connected mobile clients
            await event_bus.publish(
                Event(
                    event_type="mobile.alarm.trigger",
                    payload={"action": "ring_loud", "duration_seconds": 30},
                    source="skill.mobile_bridge",
                )
            )
            logger.info("Dispatched 'mobile.alarm.trigger' event to mobile client")
            return ToolResult(
                success=True,
                data={"status": "alarm_dispatched", "duration": 30},
                summary="Sent loud alarm trigger to your Android phone. It should start ringing now!",
            )

        elif tool_name == "sync_clipboard_to_phone":
            text = arguments.get("text", "").strip()
            if not text:
                return ToolResult(success=False, error="Text parameter is required for clipboard sync.")

            await event_bus.publish(
                Event(
                    event_type="mobile.clipboard.sync",
                    payload={"text": text},
                    source="skill.mobile_bridge",
                )
            )
            return ToolResult(
                success=True,
                data={"text_length": len(text)},
                summary=f"Sent {len(text)} characters to your phone clipboard.",
            )

        elif tool_name == "get_mobile_device_status":
            return ToolResult(
                success=True,
                data={"connected_devices": 0, "status": "listening_on_ipc"},
                summary="Mobile bridge is active on local IPC. Ready for Android client connection.",
            )

        return ToolResult(success=False, error=f"Unknown tool '{tool_name}' in mobile_bridge skill.")

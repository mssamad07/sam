"""
Windows Screen & GUI Automation Capability for Sam.
Enables mouse clicking, key presses, and screen navigation.
Requires Tier 2 permission for active input automation.
"""
import ctypes
from typing import Any

from sam_capabilities.base import BaseSkill, ToolDefinition, ToolParameter, ToolResult
from sam_core.logger import get_logger
from sam_core.permissions.policy import RiskTier

logger = get_logger("capabilities.gui_automation")


class GUIAutomationSkill(BaseSkill):
    """Automates mouse clicks, key presses, and screen interactions on Windows."""

    @property
    def name(self) -> str:
        return "gui_automation"

    @property
    def description(self) -> str:
        return "Simulate mouse clicks, keyboard text typing, and window shortcuts on Windows."

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="get_screen_size",
                description="Get the current Windows display resolution in pixels (width, height).",
                risk_tier=RiskTier.TIER_1_SAFE,
                parameters=[],
            ),
            ToolDefinition(
                name="mouse_click",
                description="Click at specific screen coordinates (x, y) with left or right button.",
                risk_tier=RiskTier.TIER_2_REVIEW,
                parameters=[
                    ToolParameter(
                        name="x",
                        type="integer",
                        description="X coordinate on the screen (horizontal)",
                        required=True,
                    ),
                    ToolParameter(
                        name="y",
                        type="integer",
                        description="Y coordinate on the screen (vertical)",
                        required=True,
                    ),
                    ToolParameter(
                        name="button",
                        type="string",
                        description="Mouse button to click: 'left', 'right', or 'double'",
                        required=False,
                        default="left",
                    ),
                ],
            ),
            ToolDefinition(
                name="type_text",
                description="Simulate typing text characters onto the currently active Windows window.",
                risk_tier=RiskTier.TIER_2_REVIEW,
                parameters=[
                    ToolParameter(
                        name="text",
                        type="string",
                        description="Text string to type into the focused input",
                        required=True,
                    ),
                ],
            ),
        ]

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        if tool_name == "get_screen_size":
            try:
                user32 = ctypes.windll.user32
                width = user32.GetSystemMetrics(0)
                height = user32.GetSystemMetrics(1)
                return ToolResult(
                    success=True,
                    data={"width": width, "height": height},
                    summary=f"Display resolution is {width}x{height} pixels.",
                )
            except Exception as exc:
                return ToolResult(success=False, error=f"Failed to get screen size: {exc}")

        elif tool_name == "mouse_click":
            x = arguments.get("x")
            y = arguments.get("y")
            button = arguments.get("button", "left").lower()
            if x is None or y is None:
                return ToolResult(success=False, error="Both 'x' and 'y' coordinates are required.")

            try:
                user32 = ctypes.windll.user32
                user32.SetCursorPos(int(x), int(y))
                # Left click: MOUSEEVENTF_LEFTDOWN = 0x0002, MOUSEEVENTF_LEFTUP = 0x0004
                # Right click: MOUSEEVENTF_RIGHTDOWN = 0x0008, MOUSEEVENTF_RIGHTUP = 0x0010
                if button == "right":
                    user32.mouse_event(0x0008, 0, 0, 0, 0)
                    user32.mouse_event(0x0010, 0, 0, 0, 0)
                elif button == "double":
                    user32.mouse_event(0x0002, 0, 0, 0, 0)
                    user32.mouse_event(0x0004, 0, 0, 0, 0)
                    user32.mouse_event(0x0002, 0, 0, 0, 0)
                    user32.mouse_event(0x0004, 0, 0, 0, 0)
                else:
                    user32.mouse_event(0x0002, 0, 0, 0, 0)
                    user32.mouse_event(0x0004, 0, 0, 0, 0)

                logger.info(f"Simulated mouse click at ({x}, {y}) [{button}]")
                return ToolResult(
                    success=True,
                    data={"x": x, "y": y, "button": button},
                    summary=f"Clicked at coordinates ({x}, {y}) with {button} button.",
                )
            except Exception as exc:
                return ToolResult(success=False, error=f"Mouse click simulation failed: {exc}")

        elif tool_name == "type_text":
            text = arguments.get("text", "")
            if not text:
                return ToolResult(success=False, error="Text parameter cannot be empty.")

            try:
                # Type using Windows SendInput via ctypes
                user32 = ctypes.windll.user32
                for char in text:
                    vk = user32.VkKeyScanW(ord(char))
                    if vk != -1:
                        user32.keybd_event(vk & 0xFF, 0, 0, 0)
                        user32.keybd_event(vk & 0xFF, 0, 2, 0)  # KEYEVENTF_KEYUP = 2

                logger.info(f"Simulated typing: {len(text)} characters")
                return ToolResult(
                    success=True,
                    data={"typed_length": len(text)},
                    summary=f"Typed text: '{text[:30]}...' into focused window.",
                )
            except Exception as exc:
                return ToolResult(success=False, error=f"Typing simulation failed: {exc}")

        return ToolResult(success=False, error=f"Unknown tool '{tool_name}' in gui_automation skill.")

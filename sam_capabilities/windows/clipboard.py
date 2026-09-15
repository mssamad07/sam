"""
Clipboard Management Capability for Sam.
Allows reading and writing system clipboard text.
"""
import subprocess
import sys
from typing import Any

from sam_capabilities.base import BaseSkill, ToolDefinition, ToolParameter, ToolResult
from sam_core.logger import get_logger
from sam_core.permissions.policy import RiskTier

logger = get_logger("capabilities.clipboard")


class ClipboardSkill(BaseSkill):
    """Provides system clipboard read and write access."""

    @property
    def name(self) -> str:
        return "clipboard"

    @property
    def description(self) -> str:
        return "Inspect and modify the system clipboard text."

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="get_clipboard",
                description="Get current text from the clipboard.",
                risk_tier=RiskTier.TIER_2_REVIEW,
            ),
            ToolDefinition(
                name="set_clipboard",
                description="Copy specified text to the system clipboard.",
                risk_tier=RiskTier.TIER_2_REVIEW,
                parameters=[
                    ToolParameter(name="text", type_str="string", description="Text to copy to clipboard", required=True)
                ],
            ),
        ]

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ToolResult:
        if sys.platform != "win32":
            return ToolResult(success=False, error="Clipboard is only supported on Windows.")

        try:
            if tool_name == "get_clipboard":
                proc = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                text = proc.stdout.strip()
                return ToolResult(success=True, data={"text": text, "length": len(text)})

            elif tool_name == "set_clipboard":
                text = arguments.get("text", "")
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command", f"Set-Clipboard -Value @'\n{text}\n'@"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return ToolResult(success=True, data={"copied": True, "length": len(text)})

        except Exception as exc:
            logger.error(f"Clipboard operation failed: {exc}")
            return ToolResult(success=False, error=str(exc))

        return ToolResult(success=False, error=f"Unknown tool '{tool_name}' in {self.name}")

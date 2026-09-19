"""
WhatsApp Automation Skill for Sam.
Enables opening chats and composing messages via WhatsApp Web / WhatsApp Desktop.
Requires Tier 2 permission for composing/sending messages.
"""
import urllib.parse
import webbrowser
from typing import Any

from sam_capabilities.base import BaseSkill, ToolDefinition, ToolParameter, ToolResult
from sam_core.logger import get_logger
from sam_core.permissions.policy import RiskTier

logger = get_logger("capabilities.whatsapp")


class WhatsAppSkill(BaseSkill):
    """Integrates WhatsApp Web / Desktop deep-linking for messaging."""

    @property
    def name(self) -> str:
        return "whatsapp"

    @property
    def description(self) -> str:
        return "Compose and send WhatsApp messages or open WhatsApp chats on Windows."

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="whatsapp_send_message",
                description="Compose a WhatsApp message to a phone number (with country code, e.g. +91XXXXXXXXXX).",
                risk_tier=RiskTier.TIER_2_REVIEW,
                parameters=[
                    ToolParameter(
                        name="phone_number",
                        type="string",
                        description="Recipient phone number with country code (e.g. '+919876543210' or '919876543210')",
                        required=True,
                    ),
                    ToolParameter(
                        name="message",
                        type="string",
                        description="Message content to pre-fill or send",
                        required=True,
                    ),
                ],
            ),
            ToolDefinition(
                name="whatsapp_open",
                description="Open WhatsApp Web or WhatsApp Desktop application.",
                risk_tier=RiskTier.TIER_1_SAFE,
                parameters=[],
            ),
        ]

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        if tool_name == "whatsapp_open":
            try:
                webbrowser.open("https://web.whatsapp.com")
                return ToolResult(
                    success=True,
                    data={"url": "https://web.whatsapp.com"},
                    summary="Opened WhatsApp Web in browser.",
                )
            except Exception as exc:
                return ToolResult(success=False, error=f"Failed to open WhatsApp: {exc}")

        elif tool_name == "whatsapp_send_message":
            phone = arguments.get("phone_number", "").strip()
            message = arguments.get("message", "").strip()
            if not phone:
                return ToolResult(success=False, error="Phone number is required.")
            if not message:
                return ToolResult(success=False, error="Message text cannot be empty.")

            clean_phone = "".join(c for c in phone if c.isdigit())
            encoded_msg = urllib.parse.quote_plus(message)
            link = f"https://web.whatsapp.com/send?phone={clean_phone}&text={encoded_msg}"

            try:
                webbrowser.open(link)
                logger.info(f"Dispatched WhatsApp message compose link to {clean_phone}")
                return ToolResult(
                    success=True,
                    data={"phone": clean_phone, "message": message, "url": link},
                    summary=f"Opened WhatsApp compose for +{clean_phone} with message: '{message}'.",
                )
            except Exception as exc:
                return ToolResult(success=False, error=f"Failed to launch WhatsApp: {exc}")

        return ToolResult(success=False, error=f"Unknown tool '{tool_name}' in whatsapp skill.")

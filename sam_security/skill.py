"""
Mobile Security and Anti-Theft Skill for Sam.
"""
from typing import Any

from sam_capabilities.base import BaseSkill, ToolDefinition, ToolParameter, ToolResult
from sam_core.logger import get_logger
from sam_core.permissions.policy import RiskTier
from sam_security.engine import MobileSecurityEngine

logger = get_logger("security.skill")


class MobileSecuritySkill(BaseSkill):
    """Provides Sam with anti-theft and remote mobile security controls."""

    def __init__(self, engine: MobileSecurityEngine | None = None) -> None:
        self.engine = engine or MobileSecurityEngine()

    @property
    def name(self) -> str:
        return "mobile_security"

    @property
    def description(self) -> str:
        return "Mobile device anti-theft, arming, disarming, and perimeter alarm controls."

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="get_security_status",
                description="Check the current mobile security state and alarm status.",
                parameters=[],
                risk_tier=RiskTier.TIER_1_SAFE,
            ),
            ToolDefinition(
                name="arm_security",
                description="Arm the anti-theft system. Requires PIN.",
                parameters=[
                    ToolParameter(name="pin", type="string", description="4-digit security PIN.", required=True),
                ],
                risk_tier=RiskTier.TIER_2_REVIEW,
            ),
            ToolDefinition(
                name="disarm_security",
                description="Disarm the anti-theft system. Requires PIN.",
                parameters=[
                    ToolParameter(name="pin", type="string", description="4-digit security PIN.", required=True),
                ],
                risk_tier=RiskTier.TIER_2_REVIEW,
            ),
            ToolDefinition(
                name="trigger_panic_alarm",
                description="Trigger the high-decibel siren alarm and defense protocol.",
                parameters=[
                    ToolParameter(name="reason", type="string", description="Reason for triggering alarm.", required=False),
                ],
                risk_tier=RiskTier.TIER_2_REVIEW,
            ),
        ]

    async def execute(
        self, tool_name: str, arguments: dict[str, Any], context: dict[str, Any] | None = None
    ) -> ToolResult:
        if tool_name == "get_security_status":
            return ToolResult(
                success=True,
                data={
                    "state": self.engine.state.value,
                    "is_armed": self.engine.is_armed,
                    "incidents_count": len(self.engine.intruder_log),
                },
            )

        if tool_name == "arm_security":
            pin = arguments.get("pin", "")
            success = await self.engine.arm(pin)
            if success:
                return ToolResult(
                    success=True,
                    data={"message": "Anti-Theft protection armed successfully, Boss.", "state": "armed"},
                )
            return ToolResult(success=False, error="Invalid security PIN provided.")

        if tool_name == "disarm_security":
            pin = arguments.get("pin", "")
            success = await self.engine.disarm(pin)
            if success:
                return ToolResult(
                    success=True,
                    data={"message": "Anti-Theft protection disarmed, Boss.", "state": "disarmed"},
                )
            return ToolResult(success=False, error="Invalid security PIN provided.")

        if tool_name == "trigger_panic_alarm":
            reason = arguments.get("reason", "manual_panic_trigger")
            await self.engine.trigger_alarm(reason)
            return ToolResult(
                success=True,
                data={"message": "Panic alarm triggered! Siren sounding and incident logged.", "state": "alarming"},
            )

        return ToolResult(success=False, error=f"Unknown tool: {tool_name}")

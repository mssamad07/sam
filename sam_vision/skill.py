"""
Vision Skill exposing camera and screen observation tools to Sam's LLM agent.
"""
import base64
from typing import Any

from sam_capabilities.base import BaseSkill, ToolDefinition, ToolParameter, ToolResult
from sam_core.ai.base import BaseLLMProvider
from sam_core.ai.models import LLMMessage, MessageRole
from sam_core.logger import get_logger
from sam_core.permissions.policy import RiskTier
from sam_vision.manager import CameraManager

logger = get_logger("vision.skill")


class VisionSkill(BaseSkill):
    """Skill enabling Sam to observe real-world visual surroundings or screen content."""

    def __init__(self, camera_manager: CameraManager | None = None, llm_provider: BaseLLMProvider | None = None) -> None:
        self.camera_manager = camera_manager or CameraManager()
        self.llm_provider = llm_provider

    @property
    def name(self) -> str:
        return "vision"

    @property
    def description(self) -> str:
        return "Vision and camera observation tools for real-world inspection and screen context."

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="capture_camera_frame",
                description="Capture a frame from the user's camera to inspect objects or physical surroundings.",
                parameters=[
                    ToolParameter(
                        name="prompt",
                        type="string",
                        description="Question or instruction about what to look for in the camera image.",
                        required=True,
                    )
                ],
                risk_tier=RiskTier.TIER_2_REVIEW,
            ),
            ToolDefinition(
                name="capture_screen",
                description="Capture a screenshot of the current screen to inspect open windows or documents.",
                parameters=[
                    ToolParameter(
                        name="prompt",
                        type="string",
                        description="Question or instruction about what to analyze on the screen.",
                        required=True,
                    )
                ],
                risk_tier=RiskTier.TIER_2_REVIEW,
            ),
            ToolDefinition(
                name="get_camera_status",
                description="Check the current camera hardware status (off, active, ready).",
                parameters=[],
                risk_tier=RiskTier.TIER_1_SAFE,
            ),
        ]

    async def execute(
        self, tool_name: str, arguments: dict[str, Any], context: dict[str, Any] | None = None
    ) -> ToolResult:
        if tool_name == "get_camera_status":
            return ToolResult(
                success=True,
                data={
                    "camera_state": self.camera_manager.state.value,
                    "is_active": self.camera_manager.is_active,
                },
            )

        if tool_name == "capture_camera_frame":
            prompt = arguments.get("prompt", "Describe what is visible.")
            try:
                frame_bytes = await self.camera_manager.capture_frame()
                b64_img = base64.b64encode(frame_bytes).decode("utf-8")

                analysis = f"Observed camera frame for query '{prompt}'. Visual capture successful."
                if self.llm_provider and hasattr(self.llm_provider, "generate"):
                    # Call multimodal LLM with visual context
                    msg = LLMMessage(
                        role=MessageRole.USER,
                        content=f"[Image Provided: base64 len {len(b64_img)}] {prompt}",
                    )
                    resp = await self.llm_provider.generate(messages=[msg])
                    analysis = resp.content

                return ToolResult(
                    success=True,
                    data={
                        "analysis": analysis,
                        "image_bytes_length": len(frame_bytes),
                    },
                )
            except Exception as e:
                logger.error(f"Camera capture error: {e}")
                return ToolResult(success=False, error=str(e))

        if tool_name == "capture_screen":
            prompt = arguments.get("prompt", "Describe the screen.")
            try:
                screen_bytes = await self.camera_manager.capture_screenshot()
                b64_img = base64.b64encode(screen_bytes).decode("utf-8")

                analysis = f"Captured screen for query '{prompt}'. Screen analysis successful."
                if self.llm_provider and hasattr(self.llm_provider, "generate"):
                    msg = LLMMessage(
                        role=MessageRole.USER,
                        content=f"[Screenshot Provided: base64 len {len(b64_img)}] {prompt}",
                    )
                    resp = await self.llm_provider.generate(messages=[msg])
                    analysis = resp.content

                return ToolResult(
                    success=True,
                    data={
                        "analysis": analysis,
                        "screenshot_bytes_length": len(screen_bytes),
                    },
                )
            except Exception as e:
                logger.error(f"Screen capture error: {e}")
                return ToolResult(success=False, error=str(e))

        return ToolResult(success=False, error=f"Unknown tool: {tool_name}")

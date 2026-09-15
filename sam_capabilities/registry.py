"""
SkillRegistry for registering, retrieving, and discovering skills in Sam.
Provides duplicate registration protection, tool indexing, and permission-gated execution.
"""
from typing import Any

from sam_capabilities.base import BaseSkill, ToolDefinition, ToolResult
from sam_core.events.bus import event_bus
from sam_core.events.types import ToolExecutedEvent
from sam_core.logger import get_logger
from sam_core.permissions.manager import permission_manager
from sam_core.permissions.policy import RiskTier

logger = get_logger("capabilities.registry")


class SkillRegistry:
    """Central registry for all active skills and tools in the system."""

    def __init__(self):
        self._skills: dict[str, BaseSkill] = {}
        self._tool_map: dict[str, tuple[BaseSkill, ToolDefinition]] = {}

    def register(self, skill: BaseSkill) -> None:
        """
        Register a new skill.
        Raises ValueError if a skill with the same name is already registered.
        """
        if skill.name in self._skills:
            raise ValueError(f"Skill '{skill.name}' is already registered in registry.")

        self._skills[skill.name] = skill
        for tool_def in skill.get_tools():
            self._tool_map[tool_def.name] = (skill, tool_def)

        logger.info(f"Registered skill '{skill.name}' (v{skill.version}) with {len(skill.get_tools())} tools")

    def get_skill(self, skill_name: str) -> BaseSkill | None:
        """Retrieve a registered skill by name, or None if not found."""
        return self._skills.get(skill_name)

    def has_skill(self, skill_name: str) -> bool:
        """Check if a skill is registered."""
        return skill_name in self._skills

    def list_skills(self) -> list[BaseSkill]:
        """Return a list of all currently registered skills."""
        return list(self._skills.values())

    def unregister(self, skill_name: str) -> bool:
        """
        Unregister a skill by name and remove its indexed tools.
        Returns True if the skill was removed, False if not found.
        """
        if skill_name in self._skills:
            del self._skills[skill_name]
            self._tool_map = {
                t_name: (s, td)
                for t_name, (s, td) in self._tool_map.items()
                if s.name != skill_name
            }
            logger.info(f"Unregistered skill '{skill_name}'")
            return True
        return False

    def get_tool_definition(self, tool_name: str) -> ToolDefinition | None:
        """Retrieve tool metadata by tool name."""
        entry = self._tool_map.get(tool_name)
        return entry[1] if entry else None

    def export_gemini_tools(self) -> list[dict[str, Any]]:
        """Export all registered tools in Google Gemini function declaration format."""
        return [td.to_gemini_dict() for _, td in self._tool_map.values()]

    def export_openai_tools(self) -> list[dict[str, Any]]:
        """Export all registered tools in OpenAI tool declaration format."""
        return [td.to_openai_dict() for _, td in self._tool_map.values()]

    async def execute_tool(
        self,
        call_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
        confirmation_token: str | None = None,
    ) -> ToolResult:
        """
        Safely execute a tool with permission evaluation.
        """
        if tool_name not in self._tool_map:
            error_msg = f"Unknown tool '{tool_name}'. Not available in registry."
            logger.error(error_msg)
            return ToolResult(success=False, error=error_msg)

        skill, tool_def = self._tool_map[tool_name]

        # 1. Evaluate safety tier
        if tool_def.risk_tier == RiskTier.TIER_3_CRITICAL and (
            not confirmation_token
            or not permission_manager.check_authorization(
                confirmation_token, tool_name=tool_name, arguments=arguments
            )
        ):
            token = await permission_manager.request_permission(
                tool_name=tool_name,
                arguments=arguments,
                description=f"Tool '{tool_name}' requires explicit confirmation: {arguments}",
                risk_tier=tool_def.risk_tier,
            )
            return ToolResult(
                success=False,
                confirmation_required=True,
                confirmation_token=token,
                message=f"Action '{tool_name}' requires confirmation. Token: {token}",
            )

        # 2. Execute within Skill
        try:
            result = await skill.execute(tool_name, arguments, context)
        except Exception as exc:
            logger.error(f"Error executing tool '{tool_name}': {exc}", exc_info=True)
            result = ToolResult(success=False, error=f"Execution error: {exc}")

        # 3. Broadcast execution event
        await event_bus.publish(
            ToolExecutedEvent(
                call_id=call_id,
                tool_name=tool_name,
                success=result.success,
                result=result.data,
                error=result.error,
            )
        )

        return result

    def clear(self) -> None:
        """Remove all registered skills and tools."""
        self._skills.clear()
        self._tool_map.clear()

    @property
    def count(self) -> int:
        """Return the number of registered skills."""
        return len(self._skills)


# Global singleton instance
skill_registry = SkillRegistry()

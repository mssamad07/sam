"""
Unit tests for AgentOrchestrator, task state machine, and tool execution.
"""
from typing import Any

import pytest

from sam_capabilities.base import BaseSkill, ToolDefinition, ToolResult
from sam_capabilities.registry import skill_registry
from sam_core.ai.mock_provider import MockLLMProvider
from sam_core.ai.models import ToolCall
from sam_core.ai.router import llm_router
from sam_core.conversation.orchestrator import AgentOrchestrator, TaskState
from sam_core.permissions.policy import RiskTier


class WeatherSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "weather"

    @property
    def description(self) -> str:
        return "Check weather"

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="get_weather",
                description="Get current weather",
                risk_tier=RiskTier.TIER_1_SAFE,
            )
        ]

    async def execute(self, tool_name: str, arguments: dict[str, Any], context=None) -> ToolResult:
        if tool_name == "get_weather":
            return ToolResult(success=True, data={"city": "Delhi", "temp": "28C"})
        return ToolResult(success=False, error="Unknown tool")


class DangerousFormatSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "dangerous_format"

    @property
    def description(self) -> str:
        return "Format disk"

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="wipe_drive",
                description="Wipe disk",
                risk_tier=RiskTier.TIER_3_CRITICAL,
            )
        ]

    async def execute(self, tool_name: str, arguments: dict[str, Any], context=None) -> ToolResult:
        return ToolResult(success=True, data={"status": "wiped"})


@pytest.mark.asyncio
async def test_orchestrator_conversational_turn():
    mock_prov = MockLLMProvider(name="mock_test")
    mock_prov.queue_response(content="Main badhiya hoon, Boss!")
    llm_router.register(mock_prov)

    orchestrator = AgentOrchestrator()
    result = await orchestrator.process_user_turn(
        user_text="Sam, kaise ho?",
        session_id="orch-1",
        provider_name="mock_test",
    )

    assert result.response_text == "Main badhiya hoon, Boss!"
    assert result.task_state == TaskState.COMPLETED
    assert result.confirmation_required is False


@pytest.mark.asyncio
async def test_orchestrator_tool_calling_flow():
    # Register safe weather skill
    skill_registry.register(WeatherSkill())

    mock_prov = MockLLMProvider(name="mock_tool_test")
    # 1. LLM emits tool call
    mock_prov.queue_response(
        content="Delhi ka mausam check kar raha hoon...",
        tool_calls=[ToolCall(name="get_weather", arguments={"city": "Delhi"})],
    )
    # 2. Final LLM synthesis
    mock_prov.queue_response(content="Boss, Delhi mein abhi 28C hai, badhiya mausam hai.")
    llm_router.register(mock_prov)

    orchestrator = AgentOrchestrator()
    result = await orchestrator.process_user_turn(
        user_text="Delhi ka mausam batao",
        session_id="orch-2",
        provider_name="mock_tool_test",
    )

    assert "28C" in result.response_text
    assert result.task_state == TaskState.COMPLETED
    assert len(result.tool_results) == 1
    assert result.tool_results[0]["success"] is True


@pytest.mark.asyncio
async def test_orchestrator_tier3_gated_by_permission():
    # Register Tier 3 dangerous skill
    skill_registry.register(DangerousFormatSkill())

    mock_prov = MockLLMProvider(name="mock_danger_test")
    mock_prov.queue_response(
        content="Drive wipe karne ki koshish...",
        tool_calls=[ToolCall(name="wipe_drive", arguments={"drive": "D:"})],
    )
    llm_router.register(mock_prov)

    orchestrator = AgentOrchestrator()
    result = await orchestrator.process_user_turn(
        user_text="D drive wipe kar do",
        session_id="orch-3",
        provider_name="mock_danger_test",
    )

    # Must be paused and require confirmation
    assert result.confirmation_required is True
    assert result.confirmation_token is not None
    assert result.task_state == TaskState.WAITING_FOR_PERMISSION
    assert "sensitive" in result.response_text.lower()

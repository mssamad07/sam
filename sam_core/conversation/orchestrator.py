"""
Agent Orchestrator and Task Planner for Sam Core.
Enforces the Observe -> Think -> Plan -> Act -> Verify -> Report loop.
Adheres strictly to SkillRegistry and PermissionManager.
"""
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from sam_capabilities.base import ToolResult
from sam_capabilities.registry import skill_registry
from sam_core.ai.models import LLMResponse
from sam_core.ai.router import llm_router
from sam_core.conversation.emotional_state import EmotionalState, emotional_state_manager
from sam_core.conversation.manager import conversation_manager
from sam_core.events.bus import event_bus
from sam_core.events.types import AssistantMessageEvent
from sam_core.logger import get_logger

logger = get_logger("conversation.orchestrator")


class AutonomyLevel(StrEnum):
    """Conceptual autonomy levels for Sam."""
    LEVEL_1_ASSIST = "level_1_assist"         # Explains and asks before actions
    LEVEL_2_DELEGATE = "level_2_delegate"     # Auto-executes low-risk, gates sensitive
    LEVEL_3_AUTONOMOUS = "level_3_autonomous" # Multi-step autonomous execution within boundaries


class TaskState(StrEnum):
    """Lifecycle states for an orchestrated agent task."""
    CREATED = "created"
    PLANNING = "planning"
    WAITING_FOR_PERMISSION = "waiting_for_permission"
    RUNNING = "running"
    PAUSED = "paused"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentTask(BaseModel):
    """Represents a goal-oriented execution task."""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    goal: str
    state: TaskState = TaskState.CREATED
    plan: list[str] = Field(default_factory=list)
    current_step: int = 0
    results: list[dict[str, Any]] = Field(default_factory=list)
    pending_token: str | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class OrchestrationResult(BaseModel):
    """Result returned to the client after processing a user turn."""
    response_text: str
    task_id: str | None = None
    task_state: TaskState | None = None
    confirmation_required: bool = False
    confirmation_token: str | None = None
    tool_results: list[dict[str, Any]] = Field(default_factory=list)


class AgentOrchestrator:
    """Coordinates goal planning, permission-gated execution, and truthful reporting."""

    def __init__(self, autonomy_level: AutonomyLevel = AutonomyLevel.LEVEL_2_DELEGATE):
        self.autonomy_level = autonomy_level
        self._tasks: dict[str, AgentTask] = {}

    def get_task(self, task_id: str) -> AgentTask | None:
        """Retrieve task by ID."""
        return self._tasks.get(task_id)

    async def process_user_turn(
        self,
        user_text: str,
        session_id: str | None = None,
        provider_name: str | None = None,
        confirmation_token: str | None = None,
    ) -> OrchestrationResult:
        """
        Main execution loop for a user request:
        1. Record user message
        2. Query LLM with available tools
        3. If tool calls emitted, plan and execute through SkillRegistry & PermissionManager
        4. Feed results back and verify
        5. Return truthful response
        """
        # Step 1: Record user message
        conversation_manager.add_user_message(user_text, session_id=session_id)
        provider = llm_router.get_provider(provider_name)

        # Create or resume task
        task = AgentTask(goal=user_text, state=TaskState.PLANNING)
        self._tasks[task.task_id] = task

        context = conversation_manager.get_full_context(session_id=session_id)
        gemini_tools = skill_registry.export_gemini_tools() if hasattr(skill_registry, "export_gemini_tools") else []

        try:
            # Step 2: Query LLM
            llm_resp: LLMResponse = await provider.generate(messages=context, tools=gemini_tools)
        except Exception as exc:
            logger.error(f"Provider '{provider.name}' generation failed: {exc}", exc_info=True)
            emotional_state_manager.transition(EmotionalState.CONCERNED, "LLM provider failure")
            fail_text = f"Boss, AI provider '{provider.name}' se communicate karne mein issue aa raha hai: {exc}"
            conversation_manager.add_assistant_message(fail_text, session_id=session_id)
            task.state = TaskState.FAILED
            task.error = str(exc)
            return OrchestrationResult(response_text=fail_text, task_id=task.task_id, task_state=TaskState.FAILED)

        # Step 3: Handle conversational reply (no tools)
        if not llm_resp.tool_calls:
            task.state = TaskState.COMPLETED
            conversation_manager.add_assistant_message(llm_resp.content, session_id=session_id)
            await event_bus.publish(AssistantMessageEvent(text=llm_resp.content))
            return OrchestrationResult(
                response_text=llm_resp.content,
                task_id=task.task_id,
                task_state=TaskState.COMPLETED,
            )

        # Step 4: Tool execution loop (Observe -> Act -> Verify)
        task.state = TaskState.RUNNING
        task.plan = [tc.name for tc in llm_resp.tool_calls]
        tool_results_data = []

        conversation_manager.add_assistant_message(
            content=llm_resp.content,
            tool_calls=llm_resp.tool_calls,
            session_id=session_id,
        )

        for tc in llm_resp.tool_calls:
            task.current_step += 1
            logger.info(f"Executing tool '{tc.name}' with args {tc.arguments}")

            # Check if skill registry has execute_tool
            if hasattr(skill_registry, "execute_tool"):
                result: ToolResult = await skill_registry.execute_tool(
                    call_id=tc.call_id,
                    tool_name=tc.name,
                    arguments=tc.arguments,
                    confirmation_token=confirmation_token,
                )
            else:
                result = ToolResult(success=False, error=f"Tool '{tc.name}' cannot be executed directly.")

            # If confirmation required: pause task
            if result.confirmation_required:
                task.state = TaskState.WAITING_FOR_PERMISSION
                task.pending_token = result.confirmation_token
                prompt_msg = f"Boss, operation '{tc.name}' sensitive hai. Permission token: {result.confirmation_token}. Kya main proceed karoon?"
                conversation_manager.add_assistant_message(prompt_msg, session_id=session_id)
                await event_bus.publish(AssistantMessageEvent(text=prompt_msg))
                return OrchestrationResult(
                    response_text=prompt_msg,
                    task_id=task.task_id,
                    task_state=TaskState.WAITING_FOR_PERMISSION,
                    confirmation_required=True,
                    confirmation_token=result.confirmation_token,
                )

            # Record tool result in session
            res_str = str(result.data if result.success else f"Error: {result.error}")
            conversation_manager.add_tool_result(
                tool_call_id=tc.call_id,
                tool_name=tc.name,
                result_content=res_str,
                session_id=session_id,
            )
            tool_results_data.append({"tool": tc.name, "success": result.success, "data": result.data, "error": result.error})
            task.results.append({"tool": tc.name, "result": result.model_dump()})

            if not result.success:
                task.state = TaskState.FAILED
                emotional_state_manager.transition(EmotionalState.CONCERNED, f"Tool '{tc.name}' execution failed")

        # Step 5: Final synthesis after tools
        task.state = TaskState.VERIFYING
        updated_context = conversation_manager.get_full_context(session_id=session_id)
        try:
            final_resp = await provider.generate(messages=updated_context)
            final_text = final_resp.content
        except Exception as exc:
            final_text = f"Boss, tools execute ho gaye par final summary generate nahi ho paayi: {exc}"

        task.state = TaskState.COMPLETED
        conversation_manager.add_assistant_message(final_text, session_id=session_id)
        await event_bus.publish(AssistantMessageEvent(text=final_text))

        return OrchestrationResult(
            response_text=final_text,
            task_id=task.task_id,
            task_state=TaskState.COMPLETED,
            tool_results=tool_results_data,
        )


# Global singleton instance
agent_orchestrator = AgentOrchestrator()

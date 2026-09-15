"""
ConversationManager for Sam Core.
Manages multi-turn conversation sessions, context assembly, language adaptation, and message budgeting.
"""
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from sam_core.ai.models import LLMMessage, MessageRole, ToolCall
from sam_core.conversation.emotional_state import emotional_state_manager
from sam_core.conversation.personality import sam_personality
from sam_core.logger import get_logger

logger = get_logger("conversation.manager")


class ConversationSession(BaseModel):
    """Represents an active multi-turn conversation session."""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    messages: list[LLMMessage] = Field(default_factory=list)
    detected_language: str = "English"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, str] = Field(default_factory=dict)


class ConversationManager:
    """Coordinates conversation sessions and context windows."""

    def __init__(self, max_context_messages: int = 40):
        self._sessions: dict[str, ConversationSession] = {}
        self._max_context_messages = max_context_messages
        self._active_session_id: str | None = None

    def get_or_create_session(self, session_id: str | None = None) -> ConversationSession:
        """Retrieve existing session or create a new one."""
        sid = session_id or self._active_session_id or str(uuid.uuid4())
        if sid not in self._sessions:
            session = ConversationSession(session_id=sid)
            self._sessions[sid] = session
            logger.info(f"Created new conversation session '{sid}'")
        self._active_session_id = sid
        return self._sessions[sid]

    def add_user_message(self, text: str, session_id: str | None = None) -> LLMMessage:
        """Add a user message and update language detection and emotional state."""
        session = self.get_or_create_session(session_id)
        # Adapt language
        lang = sam_personality.detect_language(text)
        session.detected_language = lang
        # Update emotional state
        emotional_state_manager.evaluate_turn(text)

        msg = LLMMessage(role=MessageRole.USER, content=text)
        session.messages.append(msg)
        session.updated_at = datetime.now(UTC)
        self._apply_budget(session)
        return msg

    def add_assistant_message(
        self,
        content: str,
        tool_calls: list[ToolCall] | None = None,
        session_id: str | None = None,
    ) -> LLMMessage:
        """Add an assistant completion to session history."""
        session = self.get_or_create_session(session_id)
        msg = LLMMessage(
            role=MessageRole.ASSISTANT,
            content=content,
            tool_calls=tool_calls or [],
        )
        session.messages.append(msg)
        session.updated_at = datetime.now(UTC)
        self._apply_budget(session)
        return msg

    def add_tool_result(
        self,
        tool_call_id: str,
        tool_name: str,
        result_content: str,
        session_id: str | None = None,
    ) -> LLMMessage:
        """Add a tool execution result to session history."""
        session = self.get_or_create_session(session_id)
        msg = LLMMessage(
            role=MessageRole.TOOL,
            content=result_content,
            tool_call_id=tool_call_id,
            name=tool_name,
        )
        session.messages.append(msg)
        session.updated_at = datetime.now(UTC)
        self._apply_budget(session)
        return msg

    def get_full_context(self, session_id: str | None = None) -> list[LLMMessage]:
        """
        Assemble the complete context payload for LLM consumption:
        Includes current system prompt followed by session messages.
        """
        session = self.get_or_create_session(session_id)
        sys_prompt = sam_personality.build_system_prompt(
            detected_language=session.detected_language,
            emotional_context=emotional_state_manager.context,
        )
        context = [LLMMessage(role=MessageRole.SYSTEM, content=sys_prompt)]
        context.extend(session.messages)
        return context

    def clear_session(self, session_id: str | None = None) -> None:
        """Clear conversation history for a session."""
        session = self.get_or_create_session(session_id)
        session.messages.clear()
        session.updated_at = datetime.now(UTC)
        logger.info(f"Cleared history for session '{session.session_id}'")

    def _apply_budget(self, session: ConversationSession) -> None:
        """Slide context window if history exceeds max message budget."""
        if len(session.messages) > self._max_context_messages:
            # Retain the most recent messages
            trimmed = session.messages[-self._max_context_messages:]
            session.messages = trimmed
            logger.debug(f"Trimmed session '{session.session_id}' history to {len(trimmed)} messages")


# Global singleton instance
conversation_manager = ConversationManager()

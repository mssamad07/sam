"""
Internal emotional and contextual state system for Sam.
Influences response tone, empathy, and phrasing without manipulative dependency.
"""
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from sam_core.logger import get_logger

logger = get_logger("conversation.emotion")


class EmotionalState(StrEnum):
    """Behavioral and tonal context states for Sam."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    CONCERNED = "concerned"
    FOCUSED = "focused"
    FRUSTRATED = "frustrated"
    CURIOUS = "curious"
    EXCITED = "excited"
    CALM = "calm"


class EmotionalContext(BaseModel):
    """Snapshot of active emotional state and triggering context."""
    current_state: EmotionalState = EmotionalState.CALM
    reason: str | None = "initialization"
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def tone_guidance(self) -> str:
        """Prompt instruction guiding response tone according to current state."""
        guidance_map: dict[EmotionalState, str] = {
            EmotionalState.CALM: "Maintain a steady, composed, reassuring tone. Clear and grounded.",
            EmotionalState.HAPPY: "Warm, supportive, and engaged. Celebrate wins smoothly without cheesy hype.",
            EmotionalState.CONCERNED: "Attentive, careful, and alert. If an action or system state seems risky, politely point it out.",
            EmotionalState.FOCUSED: "Crisp, analytical, and direct. Prioritize precision and step-by-step problem solving.",
            EmotionalState.FRUSTRATED: "Acknowledge obstacles honestly ('Yeh approach kaam nahi kar rahi, Boss'). Stay constructive.",
            EmotionalState.CURIOUS: "Inquisitive and observant. Ask clarifying questions where genuinely helpful.",
            EmotionalState.EXCITED: "Energetic and motivated, but mature and realistic.",
            EmotionalState.NEUTRAL: "Objective, efficient, and direct.",
        }
        return guidance_map.get(self.current_state, "Calm, intelligent, and direct.")


class EmotionalStateManager:
    """Manages emotional context transitions safely."""

    def __init__(self, initial_state: EmotionalState = EmotionalState.CALM):
        self._context = EmotionalContext(current_state=initial_state, reason="Startup")

    @property
    def current_state(self) -> EmotionalState:
        return self._context.current_state

    @property
    def context(self) -> EmotionalContext:
        return self._context

    def transition(self, new_state: EmotionalState, reason: str) -> None:
        """Explicit state transition."""
        old_state = self._context.current_state
        self._context = EmotionalContext(
            current_state=new_state,
            reason=reason,
            updated_at=datetime.now(UTC),
        )
        logger.debug(f"EmotionalState transition: {old_state} -> {new_state} (Reason: {reason})")

    def evaluate_turn(self, user_text: str, has_error: bool = False, is_high_risk: bool = False) -> None:
        """Heuristic transition based on conversational and execution triggers."""
        if has_error:
            self.transition(EmotionalState.CONCERNED, "Tool execution failure or system error detected")
        elif is_high_risk:
            self.transition(EmotionalState.CONCERNED, "High-consequence operation requested")
        elif any(w in user_text.lower() for w in ["problem", "issue", "bug", "crash", "stuck", "error"]):
            self.transition(EmotionalState.FOCUSED, "Troubleshooting / technical problem solving")
        elif any(w in user_text.lower() for w in ["shabaash", "great", "awesome", "badhiya", "thanks", "done"]):
            self.transition(EmotionalState.HAPPY, "Positive task accomplishment")
        elif any(w in user_text.lower() for w in ["analyze", "design", "plan", "build", "code"]):
            self.transition(EmotionalState.FOCUSED, "Deep engineering task")
        else:
            self.transition(EmotionalState.CALM, "Normal interaction")


# Global singleton instance
emotional_state_manager = EmotionalStateManager()

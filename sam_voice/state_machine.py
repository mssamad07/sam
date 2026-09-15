"""
Voice State Machine enforcing valid state transitions, event publishing, and safety resets.
"""
import time
from typing import ClassVar

from sam_core.events.bus import EventBus, get_event_bus
from sam_core.events.types import Event
from sam_core.logger import get_logger
from sam_voice.events import VOICE_STATE_CHANGED, VoiceStateChangedEvent
from sam_voice.states import VoiceState

logger = get_logger("voice.state_machine")


class InvalidVoiceStateTransition(Exception):
    """Raised when an illegal voice state transition is requested."""
    pass


class VoiceStateMachine:
    """
    Enforces allowed transitions between VoiceState values and publishes state change events.
    """

    VALID_TRANSITIONS: ClassVar[dict[VoiceState, set[VoiceState]]] = {
        VoiceState.IDLE: {
            VoiceState.WAKE_DETECTED,
            VoiceState.LISTENING,
            VoiceState.ERROR,
        },
        VoiceState.WAKE_DETECTED: {
            VoiceState.LISTENING,
            VoiceState.IDLE,
            VoiceState.ERROR,
        },
        VoiceState.LISTENING: {
            VoiceState.PROCESSING,
            VoiceState.IDLE,
            VoiceState.ERROR,
        },
        VoiceState.PROCESSING: {
            VoiceState.SPEAKING,
            VoiceState.WAITING_FOR_PERMISSION,
            VoiceState.IDLE,
            VoiceState.ERROR,
        },
        VoiceState.WAITING_FOR_PERMISSION: {
            VoiceState.PROCESSING,
            VoiceState.SPEAKING,
            VoiceState.IDLE,
            VoiceState.ERROR,
        },
        VoiceState.SPEAKING: {
            VoiceState.IDLE,
            VoiceState.INTERRUPTED,
            VoiceState.ERROR,
        },
        VoiceState.INTERRUPTED: {
            VoiceState.LISTENING,
            VoiceState.IDLE,
            VoiceState.ERROR,
        },
        VoiceState.ERROR: {
            VoiceState.IDLE,
            VoiceState.LISTENING,
        },
    }

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self._current_state = VoiceState.IDLE
        self._state_entered_at = time.time()
        self._event_bus = event_bus or get_event_bus()
        self._transition_history: list[tuple[VoiceState, VoiceState, str, float]] = []

    @property
    def current_state(self) -> VoiceState:
        return self._current_state

    @property
    def state_duration(self) -> float:
        return time.time() - self._state_entered_at

    @property
    def history(self) -> list[tuple[VoiceState, VoiceState, str, float]]:
        return list(self._transition_history)

    async def transition_to(self, target_state: VoiceState, reason: str = "") -> None:
        if target_state == self._current_state:
            return

        allowed = self.VALID_TRANSITIONS.get(self._current_state, set())
        if target_state not in allowed:
            err = (
                f"Illegal transition from {self._current_state.value} to "
                f"{target_state.value} (reason: {reason})"
            )
            logger.error(err)
            raise InvalidVoiceStateTransition(err)

        old_state = self._current_state
        self._current_state = target_state
        self._state_entered_at = time.time()
        self._transition_history.append((old_state, target_state, reason, self._state_entered_at))

        logger.info(f"Voice state: {old_state.value} -> {target_state.value} ({reason})")

        await self._event_bus.publish(
            Event(
                event_type=VOICE_STATE_CHANGED,
                payload=VoiceStateChangedEvent(
                    old_state=old_state,
                    new_state=target_state,
                    reason=reason,
                ).model_dump(),
                source="voice.state_machine",
            )
        )

    async def reset(self, reason: str = "manual_reset") -> None:
        old_state = self._current_state
        self._current_state = VoiceState.IDLE
        self._state_entered_at = time.time()
        self._transition_history.append((old_state, VoiceState.IDLE, reason, self._state_entered_at))
        await self._event_bus.publish(
            Event(
                event_type=VOICE_STATE_CHANGED,
                payload=VoiceStateChangedEvent(
                    old_state=old_state,
                    new_state=VoiceState.IDLE,
                    reason=reason,
                ).model_dump(),
                source="voice.state_machine",
            )
        )

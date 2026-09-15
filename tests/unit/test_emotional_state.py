"""
Unit tests for internal emotional state machine and tone guidance.
"""
from sam_core.conversation.emotional_state import EmotionalState, EmotionalStateManager


def test_state_transitions():
    mgr = EmotionalStateManager(initial_state=EmotionalState.CALM)
    assert mgr.current_state == EmotionalState.CALM

    mgr.transition(EmotionalState.FOCUSED, "User requested code architecture")
    assert mgr.current_state == EmotionalState.FOCUSED
    assert "analytical" in mgr.context.tone_guidance.lower()


def test_heuristic_context_evaluation():
    mgr = EmotionalStateManager()

    # Error trigger
    mgr.evaluate_turn("Normal input", has_error=True)
    assert mgr.current_state == EmotionalState.CONCERNED

    # High risk trigger
    mgr.evaluate_turn("Normal input", is_high_risk=True)
    assert mgr.current_state == EmotionalState.CONCERNED

    # Troubleshooting keyword trigger
    mgr.evaluate_turn("Boss, server crash ho gaya bug aa raha hai")
    assert mgr.current_state == EmotionalState.FOCUSED

    # Success / praise keyword trigger
    mgr.evaluate_turn("Great job Sam! Badhiya kaam kiya")
    assert mgr.current_state == EmotionalState.HAPPY

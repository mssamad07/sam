"""
Voice pipeline state definitions for Sam.
"""
from enum import StrEnum


class VoiceState(StrEnum):
    """
    Explicit lifecycle states for the Sam Voice Pipeline.
    """
    IDLE = "idle"
    WAKE_DETECTED = "wake_detected"
    LISTENING = "listening"
    PROCESSING = "processing"
    WAITING_FOR_PERMISSION = "waiting_for_permission"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    ERROR = "error"

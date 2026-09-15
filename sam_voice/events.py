"""
Typed event models for Voice Pipeline.
"""
from pydantic import BaseModel, Field

from sam_voice.states import VoiceState

VOICE_STATE_CHANGED = "voice.state_changed"
VOICE_WAKE_DETECTED = "voice.wake_detected"
VOICE_SPEECH_STARTED = "voice.speech_started"
VOICE_SPEECH_ENDED = "voice.speech_ended"
VOICE_TRANSCRIPTION = "voice.transcription"
VOICE_TTS_STARTED = "voice.tts_started"
VOICE_TTS_FINISHED = "voice.tts_finished"
VOICE_BARGE_IN = "voice.barge_in"
VOICE_ERROR = "voice.error"


class VoiceStateChangedEvent(BaseModel):
    old_state: VoiceState
    new_state: VoiceState
    reason: str = ""


class WakeDetectedEvent(BaseModel):
    wake_word: str
    confidence: float = Field(default=0.95, ge=0.0, le=1.0)


class SpeechSegmentEvent(BaseModel):
    duration_seconds: float
    sample_rate: int = 16000


class TranscriptionEvent(BaseModel):
    text: str
    confidence: float = 1.0
    language: str = "en"
    latency_ms: float = 0.0


class BargeInEvent(BaseModel):
    interrupted_at_seconds: float = 0.0
    reason: str = "user_speech_detected"

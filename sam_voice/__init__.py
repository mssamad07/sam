"""
Voice Engine module for Sam.
"""
from sam_voice.audio_io import AudioPlayer
from sam_voice.events import (
    VOICE_BARGE_IN,
    VOICE_ERROR,
    VOICE_SPEECH_ENDED,
    VOICE_SPEECH_STARTED,
    VOICE_STATE_CHANGED,
    VOICE_TRANSCRIPTION,
    VOICE_TTS_FINISHED,
    VOICE_TTS_STARTED,
    VOICE_WAKE_DETECTED,
    BargeInEvent,
    SpeechSegmentEvent,
    TranscriptionEvent,
    VoiceStateChangedEvent,
    WakeDetectedEvent,
)
from sam_voice.pipeline import VoicePipeline
from sam_voice.state_machine import InvalidVoiceStateTransition, VoiceStateMachine
from sam_voice.states import VoiceState
from sam_voice.stt.base import BaseSTTProvider, TranscriptionResult
from sam_voice.tts.base import BaseTTSProvider, SynthesisResult
from sam_voice.vad import BaseVAD, EnergyVAD
from sam_voice.wake_word import BaseWakeWordDetector, MockWakeWordDetector, OpenWakeWordDetector

__all__ = [
    "AudioPlayer",
    "BargeInEvent",
    "BaseSTTProvider",
    "BaseTTSProvider",
    "BaseVAD",
    "BaseWakeWordDetector",
    "EnergyVAD",
    "InvalidVoiceStateTransition",
    "MockSTTProvider",
    "MockTTSProvider",
    "MockWakeWordDetector",
    "OpenWakeWordDetector",
    "SpeechSegmentEvent",
    "SynthesisResult",
    "TranscriptionEvent",
    "TranscriptionResult",
    "VOICE_BARGE_IN",
    "VOICE_ERROR",
    "VOICE_SPEECH_ENDED",
    "VOICE_SPEECH_STARTED",
    "VOICE_STATE_CHANGED",
    "VOICE_TRANSCRIPTION",
    "VOICE_TTS_FINISHED",
    "VOICE_TTS_STARTED",
    "VOICE_WAKE_DETECTED",
    "VoicePipeline",
    "VoiceState",
    "VoiceStateChangedEvent",
    "VoiceStateMachine",
    "WakeDetectedEvent",
]

"""TTS package exports."""
from sam_voice.tts.base import BaseTTSProvider, SynthesisResult
from sam_voice.tts.edge_tts_provider import EdgeTTSProvider
from sam_voice.tts.mock_tts_provider import MockTTSProvider

__all__ = ["BaseTTSProvider", "SynthesisResult", "EdgeTTSProvider", "MockTTSProvider"]

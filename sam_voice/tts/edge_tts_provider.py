"""
Microsoft Edge TTS Provider for Sam.
Supports high-quality multilingual natural speech (English, Hindi, Hinglish).
"""
from io import BytesIO
from typing import ClassVar

import edge_tts

from sam_core.logger import get_logger
from sam_voice.tts.base import BaseTTSProvider, SynthesisResult

logger = get_logger("voice.tts.edge")


class EdgeTTSProvider(BaseTTSProvider):
    """Fast, natural, online TTS via Microsoft Edge service."""

    DEFAULT_VOICES: ClassVar[dict[str, str]] = {
        "en": "en-IN-PrabhatNeural",  # Indian English (Calm, friendly male)
        "hi": "hi-IN-MadhurNeural",   # Hindi (Warm, direct male)
        "en_us": "en-US-GuyNeural",   # US English fallback
    }

    def __init__(self, default_voice: str = "en-IN-PrabhatNeural", rate: str = "+0%") -> None:
        self.default_voice = default_voice
        self.rate = rate

    @property
    def name(self) -> str:
        return "edge_tts"

    def select_voice(self, text: str, voice_override: str | None = None) -> str:
        if voice_override:
            return voice_override

        # Check for Devanagari script for Hindi
        if any("\u0900" <= ch <= "\u097f" for ch in text):
            return self.DEFAULT_VOICES["hi"]

        # Check for Hinglish markers
        hinglish_markers = ["haan", "theek", "samajh", "kya", "kaise", "bhai", "boss", "achha"]
        words = text.lower().split()
        if any(m in words for m in hinglish_markers):
            return self.DEFAULT_VOICES["en"]  # Indian English handles Hinglish best

        return self.default_voice

    async def synthesize(self, text: str, voice: str | None = None) -> SynthesisResult:
        if not text.strip():
            return SynthesisResult(audio_bytes=b"", sample_rate=24000, format="mp3", duration_seconds=0.0)

        selected_voice = self.select_voice(text, voice)
        communicate = edge_tts.Communicate(text=text, voice=selected_voice)

        buffer = BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buffer.write(chunk["data"])

        audio_data = buffer.getvalue()
        duration = max(0.2, len(audio_data) / 6000.0) if audio_data else 0.0

        return SynthesisResult(
            audio_bytes=audio_data,
            sample_rate=24000,
            format="mp3",
            duration_seconds=duration,
        )

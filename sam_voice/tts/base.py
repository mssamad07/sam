"""
Text-to-Speech provider abstraction.
"""
from abc import ABC, abstractmethod

from pydantic import BaseModel


class SynthesisResult(BaseModel):
    audio_bytes: bytes
    sample_rate: int = 24000
    format: str = "mp3"
    duration_seconds: float = 0.0


class BaseTTSProvider(ABC):
    """Abstract base class for TTS providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def synthesize(self, text: str, voice: str | None = None) -> SynthesisResult:
        """Synthesize text into audio bytes."""
        pass

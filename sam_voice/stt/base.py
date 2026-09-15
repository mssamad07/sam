"""
Speech-to-Text provider abstraction.
"""
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class TranscriptionResult(BaseModel):
    text: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    language: str = "en"
    duration_seconds: float = 0.0


class BaseSTTProvider(ABC):
    """Abstract base class for STT providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""
        pass

    @abstractmethod
    async def transcribe(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        language: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe audio bytes to text."""
        pass

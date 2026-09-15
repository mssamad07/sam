"""
Cloud STT Providers: Groq Whisper, OpenAI Whisper, and Mock STT for testing.
"""
import httpx

from sam_core.logger import get_logger
from sam_voice.stt.base import BaseSTTProvider, TranscriptionResult

logger = get_logger("voice.stt")


class MockSTTProvider(BaseSTTProvider):
    """Mock STT provider for tests and automated pipelines."""

    def __init__(self, default_text: str = "Hello Sam") -> None:
        self._default_text = default_text
        self._next_result: TranscriptionResult | None = None

    @property
    def name(self) -> str:
        return "mock_stt"

    def set_next_transcription(self, result: TranscriptionResult) -> None:
        self._next_result = result

    async def transcribe(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        language: str | None = None,
    ) -> TranscriptionResult:
        if self._next_result is not None:
            res = self._next_result
            self._next_result = None
            return res
        duration = len(audio_data) / (sample_rate * 2) if sample_rate > 0 else 1.0
        return TranscriptionResult(
            text=self._default_text,
            confidence=0.98,
            language=language or "en",
            duration_seconds=duration,
        )


class GroqSTTProvider(BaseSTTProvider):
    """Groq Whisper Cloud STT Provider."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "whisper-large-v3",
        timeout: float = 10.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "groq_whisper"

    async def transcribe(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        language: str | None = None,
    ) -> TranscriptionResult:
        if not self.api_key:
            raise ValueError("Groq API key is not configured for STT")

        headers = {"Authorization": f"Bearer {self.api_key}"}
        files = {"file": ("audio.wav", audio_data, "audio/wav")}
        data = {"model": self.model}
        if language:
            data["language"] = language

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers=headers,
                files=files,
                data=data,
            )
            resp.raise_for_status()
            res_json = resp.json()
            return TranscriptionResult(
                text=res_json.get("text", "").strip(),
                confidence=0.95,
                language=language or "en",
            )

"""
Mock TTS Provider for unit testing and headless environments.
"""
from sam_voice.tts.base import BaseTTSProvider, SynthesisResult


class MockTTSProvider(BaseTTSProvider):
    """Mock TTS synthesizing synthetic bytes instantaneously."""

    def __init__(self, sample_rate: int = 16000) -> None:
        self.sample_rate = sample_rate
        self.synthesized_prompts: list[str] = []

    @property
    def name(self) -> str:
        return "mock_tts"

    async def synthesize(self, text: str, voice: str | None = None) -> SynthesisResult:
        self.synthesized_prompts.append(text)
        dummy_bytes = b"\x00\x00" * int(self.sample_rate * 0.1)
        return SynthesisResult(
            audio_bytes=dummy_bytes,
            sample_rate=self.sample_rate,
            format="wav",
            duration_seconds=0.1,
        )

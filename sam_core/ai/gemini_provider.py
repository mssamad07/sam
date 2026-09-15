"""
Google Gemini LLM Provider implementation.
Uses Google GenAI SDK or HTTP API when credentials are provided.
"""
from typing import Any

from sam_core.ai.base import BaseLLMProvider
from sam_core.ai.models import LLMMessage, LLMResponse, ProviderStatus
from sam_core.config import settings
from sam_core.logger import get_logger

logger = get_logger("ai.gemini")


class GeminiProvider(BaseLLMProvider):
    """Google Gemini Provider."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-2.0-flash",
    ):
        self._api_key = api_key or settings.gemini_api_key
        self._model = model

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return self._model

    def is_available(self) -> bool:
        return bool(self._api_key and self._api_key.strip())

    def get_status(self) -> ProviderStatus:
        available = self.is_available()
        return ProviderStatus(
            name=self.name,
            available=available,
            configured=bool(self._api_key),
            model=self._model,
            message="Ready" if available else "Missing GEMINI_API_KEY",
        )

    async def generate(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        if not self.is_available():
            raise RuntimeError(
                "GeminiProvider is not available: GEMINI_API_KEY is not configured in .env."
            )

        # In production with API key, Google GenAI client is invoked here.
        # Fallback to structured HTTP or client call:
        try:
            from google import genai
            client = genai.Client(api_key=self._api_key)
            # Format prompt & generate
            prompt = "\n".join([f"{m.role}: {m.content}" for m in messages])
            response = client.models.generate_content(
                model=self._model,
                contents=prompt,
            )
            return LLMResponse(
                content=response.text or "",
                tool_calls=[],
                provider=self.name,
                model=self._model,
            )
        except ImportError:
            # If google-genai library isn't installed yet
            raise RuntimeError(
                "google-genai package is not installed. Install with 'pip install google-genai'."
            ) from None
        except Exception as exc:
            logger.error(f"Gemini generation error: {exc}")
            raise

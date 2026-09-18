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
        model: str | None = None,
    ):
        import os

        key = api_key or settings.gemini_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        self._api_key = key.strip() if key else None
        self._model = model or getattr(settings, "gemini_model", "gemini-2.0-flash")

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
            message="Ready" if available else "Missing GEMINI_API_KEY or GOOGLE_API_KEY (configuration required in .env)",
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
                "GeminiProvider is not available: GEMINI_API_KEY or GOOGLE_API_KEY is not configured in .env or environment."
            )

        # In production with API key, Google GenAI client is invoked here if available.
        # Otherwise, fall back to direct HTTP REST call with httpx:
        try:
            from google import genai

            client = genai.Client(api_key=self._api_key)
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
            # Fallback to direct async HTTP call to Google Gemini REST endpoint
            import httpx

            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent"
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self._api_key or "",
            }
            contents_list: list[dict[str, Any]] = []
            system_instruction = None
            for m in messages:
                if m.role.value == "system":
                    system_instruction = {"parts": [{"text": m.content}]}
                else:
                    role_str = "user" if m.role.value == "user" else "model"
                    contents_list.append({
                        "role": role_str,
                        "parts": [{"text": m.content}],
                    })
            if not contents_list:
                contents_list = [{"role": "user", "parts": [{"text": "Hello"}]}]

            payload: dict[str, Any] = {"contents": contents_list}
            if system_instruction:
                payload["system_instruction"] = system_instruction
            if temperature is not None:
                payload["generationConfig"] = {"temperature": temperature}

            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(endpoint, json=payload, headers=headers)
                if res.status_code != 200:
                    raise RuntimeError(f"Gemini API request failed ({res.status_code}): {res.text}") from None
                data = res.json()
                content = ""
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    content = "".join([p.get("text", "") for p in parts if "text" in p])
                return LLMResponse(
                    content=content,
                    tool_calls=[],
                    provider=self.name,
                    model=self._model,
                )
        except Exception as exc:
            logger.error(f"Gemini generation error: {exc}")
            raise

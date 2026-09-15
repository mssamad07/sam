"""
OpenAI & Groq compatible LLM Provider implementation.
Works with any standard OpenAI-compatible completions API endpoint.
"""
from typing import Any

import httpx

from sam_core.ai.base import BaseLLMProvider
from sam_core.ai.models import LLMMessage, LLMResponse, ProviderStatus, ToolCall
from sam_core.config import settings
from sam_core.logger import get_logger

logger = get_logger("ai.openai")


class OpenAIProvider(BaseLLMProvider):
    """OpenAI / Groq API Provider."""

    def __init__(
        self,
        name: str = "openai",
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o",
    ):
        self._name = name
        self._base_url = base_url.rstrip("/")
        self._model = model

        if name == "groq":
            self._api_key = api_key or settings.groq_api_key
            self._base_url = "https://api.groq.com/openai/v1"
            self._model = model if model != "gpt-4o" else "llama-3.3-70b-versatile"
        else:
            self._api_key = api_key or settings.openai_api_key

    @property
    def name(self) -> str:
        return self._name

    @property
    def default_model(self) -> str:
        return self._model

    def is_available(self) -> bool:
        return bool(self._api_key and self._api_key.strip())

    def get_status(self) -> ProviderStatus:
        available = self.is_available()
        env_var = "GROQ_API_KEY" if self._name == "groq" else "OPENAI_API_KEY"
        return ProviderStatus(
            name=self.name,
            available=available,
            configured=bool(self._api_key),
            model=self._model,
            message="Ready" if available else f"Missing {env_var}",
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
                f"{self.name.capitalize()}Provider is not available: API key not configured."
            )

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": m.role.value, "content": m.content} for m in messages],
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = tools

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self._base_url}/chat/completions", json=payload, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"{self.name.capitalize()} API Error ({resp.status_code}): {resp.text}"
                )
            data = resp.json()

        choice = data["choices"][0]["message"]
        content = choice.get("content") or ""
        tool_calls = []

        if "tool_calls" in choice:
            import json
            for tc in choice["tool_calls"]:
                tool_calls.append(
                    ToolCall(
                        call_id=tc["id"],
                        name=tc["function"]["name"],
                        arguments=json.loads(tc["function"]["arguments"]),
                    )
                )

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            usage=data.get("usage", {}),
            finish_reason=data["choices"][0].get("finish_reason"),
            provider=self.name,
            model=self._model,
        )

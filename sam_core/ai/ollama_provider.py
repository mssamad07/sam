"""
Ollama Local Model Provider for Sam.
Enables offline and local open-source LLM inference.
"""
from typing import Any

import httpx

from sam_core.ai.base import BaseLLMProvider
from sam_core.ai.models import LLMMessage, LLMResponse, ProviderStatus
from sam_core.logger import get_logger

logger = get_logger("ai.ollama")


class OllamaProvider(BaseLLMProvider):
    """Local Ollama inference provider."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "llama3.2:latest",
    ):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._available_cache: bool | None = None

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def default_model(self) -> str:
        return self._model

    def is_available(self) -> bool:
        # Check if local Ollama daemon is reachable
        try:
            resp = httpx.get(f"{self._base_url}/api/tags", timeout=1.0)
            return resp.status_code == 200
        except Exception:
            return False

    def list_local_models(self) -> list[str]:
        """Fetch list of locally installed Ollama model tags."""
        try:
            resp = httpx.get(f"{self._base_url}/api/tags", timeout=2.0)
            if resp.status_code == 200:
                data = resp.json()
                return [m.get("name") for m in data.get("models", []) if "name" in m]
        except Exception:
            pass
        return []

    def get_status(self) -> ProviderStatus:
        available = self.is_available()
        return ProviderStatus(
            name=self.name,
            available=available,
            configured=True,
            model=self._model,
            message="Ollama running locally" if available else "Ollama daemon not reachable at 127.0.0.1:11434",
        )

    async def generate(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        if not self.is_available():
            raise RuntimeError("Ollama daemon is not running on local machine.")

        payload = {
            "model": self._model,
            "messages": [{"role": m.role.value, "content": m.content} for m in messages],
            "stream": False,
            "options": {"temperature": temperature},
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{self._base_url}/api/chat", json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Ollama error ({resp.status_code}): {resp.text}")
            data = resp.json()

        content = data.get("message", {}).get("content", "")
        return LLMResponse(
            content=content,
            tool_calls=[],
            usage={},
            provider=self.name,
            model=self._model,
        )

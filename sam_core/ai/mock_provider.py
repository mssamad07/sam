"""
Mock LLM Provider for unit testing and offline development.
Allows scripting exact responses and tool calls without network requests or API keys.
"""
from collections.abc import AsyncGenerator
from typing import Any

from sam_core.ai.base import BaseLLMProvider
from sam_core.ai.models import LLMMessage, LLMResponse, ProviderStatus, ToolCall


class MockLLMProvider(BaseLLMProvider):
    """Deterministic, mockable LLM provider for tests and simulations."""

    def __init__(
        self,
        name: str = "mock",
        default_model: str = "mock-model-v1",
        is_available_flag: bool = True,
    ):
        self._name = name
        self._default_model = default_model
        self._is_available = is_available_flag
        self.preset_responses: list[LLMResponse] = []
        self.call_history: list[list[LLMMessage]] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def default_model(self) -> str:
        return self._default_model

    def is_available(self) -> bool:
        return self._is_available

    def set_available(self, available: bool) -> None:
        self._is_available = available

    def get_status(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            available=self._is_available,
            configured=True,
            model=self._default_model,
            message="Mock provider ready",
        )

    def queue_response(
        self,
        content: str = "",
        tool_calls: list[ToolCall] | None = None,
    ) -> None:
        """Queue a predetermined response for the next completion call."""
        self.preset_responses.append(
            LLMResponse(
                content=content,
                tool_calls=tool_calls or [],
                provider=self.name,
                model=self._default_model,
            )
        )

    async def generate(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        self.call_history.append(messages)

        if not self._is_available:
            raise RuntimeError(f"Provider '{self.name}' is currently unavailable.")

        if self.preset_responses:
            return self.preset_responses.pop(0)

        # Default echo/conversational reply
        last_msg = messages[-1].content if messages else ""
        return LLMResponse(
            content=f"Boss, received: {last_msg}",
            tool_calls=[],
            provider=self.name,
            model=self._default_model,
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str]:
        resp = await self.generate(messages, tools, temperature)
        words = resp.content.split()
        for word in words:
            yield word + " "

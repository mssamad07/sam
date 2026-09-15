"""
Abstract Base Class for LLM providers in Sam.
Guarantees a unified interface for text generation, streaming, and tool calling.
"""
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from sam_core.ai.models import LLMMessage, LLMResponse, ProviderStatus


class BaseLLMProvider(ABC):
    """Abstract interface that all LLM backends must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier (e.g., 'gemini', 'openai', 'groq', 'ollama', 'mock')."""
        pass

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model name for this provider."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether the provider has valid credentials/configuration to operate."""
        pass

    @abstractmethod
    def get_status(self) -> ProviderStatus:
        """Return truthful status of the provider."""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """
        Execute completion with the model.
        Must return a structured LLMResponse or raise a clear exception.
        """
        pass

    async def stream(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str]:
        """
        Stream partial token deltas.
        Default implementation yields the complete response if streaming not natively implemented.
        """
        response = await self.generate(messages=messages, tools=tools, temperature=temperature)
        yield response.content

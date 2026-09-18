"""
LLM Router and Provider Factory for Sam.
Manages provider registration, truthful status inspection, and fallback routing.
"""

from sam_core.ai.base import BaseLLMProvider
from sam_core.ai.gemini_provider import GeminiProvider
from sam_core.ai.mock_provider import MockLLMProvider
from sam_core.ai.models import ProviderStatus
from sam_core.ai.ollama_provider import OllamaProvider
from sam_core.ai.openai_provider import OpenAIProvider
from sam_core.config import settings
from sam_core.logger import get_logger

logger = get_logger("ai.router")


class LLMRouter:
    """Central registry and router for AI/LLM providers."""

    def __init__(self):
        self._providers: dict[str, BaseLLMProvider] = {}
        self._default_provider_name: str = "mock"
        self._initialize_builtins()

    def _initialize_builtins(self) -> None:
        """Register default provider implementations."""
        gemini_model = getattr(settings, "gemini_model", "gemini-2.0-flash")
        self.register(GeminiProvider(model=gemini_model))
        self.register(OpenAIProvider(name="openai", model="gpt-4o"))
        self.register(OpenAIProvider(name="groq", model="llama-3.3-70b-versatile"))
        self.register(OllamaProvider(model="llama3.2:latest"))
        self.register(MockLLMProvider(name="mock"))

        # Default to configured provider if available, else mock
        configured = getattr(settings, "default_provider", "gemini")
        if configured in self._providers and self._providers[configured].is_available():
            self._default_provider_name = configured
        else:
            self._default_provider_name = "mock"
            if configured != "mock":
                logger.info(
                    f"Configured provider '{configured}' is unavailable; defaulting to 'mock' provider."
                )

    def register(self, provider: BaseLLMProvider) -> None:
        """Register an LLM provider."""
        self._providers[provider.name] = provider
        logger.debug(f"Registered LLM provider '{provider.name}'")

    def get_provider(self, name: str | None = None) -> BaseLLMProvider:
        """
        Retrieve a provider by name, or return the default active provider.
        Raises ValueError if requested provider is unknown.
        """
        target = name or self._default_provider_name
        if target not in self._providers:
            raise ValueError(f"Unknown LLM provider '{target}'. Available: {list(self._providers.keys())}")
        return self._providers[target]

    def set_default_provider(self, name: str) -> None:
        """Change the active default provider."""
        if name not in self._providers:
            raise ValueError(f"Unknown LLM provider '{name}'")
        self._default_provider_name = name
        logger.info(f"Default LLM provider set to '{name}'")

    def list_statuses(self) -> list[ProviderStatus]:
        """Return truthful status of all registered providers."""
        return [p.get_status() for p in self._providers.values()]


# Global singleton instance
llm_router = LLMRouter()

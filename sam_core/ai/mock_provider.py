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

        # Default conversational reply and tool calling heuristics
        last_msg = messages[-1].content if messages else ""
        lower = last_msg.lower()

        available_tool_names = [t.get("name") for t in (tools or [])] if tools else []
        tool_calls = []

        if "get_system_metrics" in available_tool_names and any(
            k in lower for k in ["cpu", "ram", "battery", "metrics", "sysinfo", "system info"]
        ):
            tool_calls.append(ToolCall(name="get_system_metrics", arguments={}))
            return LLMResponse(
                content="Checking system hardware metrics for you, Boss...",
                tool_calls=tool_calls,
                provider=self.name,
                model=self._default_model,
            )

        if "search_web" in available_tool_names and any(
            k in lower for k in ["search", "google", "weather", "look up", "find online"]
        ):
            query = last_msg.replace("search", "").replace("find online", "").strip() or "current news"
            tool_calls.append(ToolCall(name="search_web", arguments={"query": query}))
            return LLMResponse(
                content=f"Searching the web for '{query}', Boss...",
                tool_calls=tool_calls,
                provider=self.name,
                model=self._default_model,
            )

        if any(g in lower for g in ["kaise ho", "kya chal raha", "sab theek", "kaisa hai"]):
            reply = "Main badhiya hoon Boss! Sab smooth chal raha hai. Aap batao, aaj kya plan hai?"
        elif any(g in lower for g in ["namaste", "pranam", "kya haal"]):
            reply = "Namaste Boss! Hamesha ki tarah ready hoon. Batao kya karna hai."
        elif "who are you" in lower or "koun ho" in lower or "identity" in lower:
            reply = (
                "I'm Sam — your personal AI assistant and digital operator. "
                "Calm, observant, honest, and always here to help you get things done, Boss."
            )
        elif "hello" in lower or "hi" in lower or "hey" in lower:
            reply = f"Hello Boss! Received: {last_msg}. Standing by and ready to assist."
        else:
            reply = f"Boss, received: {last_msg}"

        return LLMResponse(
            content=reply,
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

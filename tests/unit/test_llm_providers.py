"""
Unit tests for LLM provider abstraction layer.
"""
import pytest

from sam_core.ai.gemini_provider import GeminiProvider
from sam_core.ai.mock_provider import MockLLMProvider
from sam_core.ai.models import LLMMessage, MessageRole, ToolCall
from sam_core.ai.openai_provider import OpenAIProvider
from sam_core.ai.router import LLMRouter


@pytest.mark.asyncio
async def test_mock_provider_generation_and_queue():
    provider = MockLLMProvider(name="test_mock")
    assert provider.is_available() is True
    assert provider.get_status().available is True

    # Default echo
    resp = await provider.generate([LLMMessage(role=MessageRole.USER, content="Hello")])
    assert "Hello" in resp.content
    assert resp.provider == "test_mock"

    # Queued response
    provider.queue_response(content="Queued answer", tool_calls=[ToolCall(name="get_time", arguments={})])
    resp2 = await provider.generate([LLMMessage(role=MessageRole.USER, content="Next")])
    assert resp2.content == "Queued answer"
    assert len(resp2.tool_calls) == 1
    assert resp2.tool_calls[0].name == "get_time"


@pytest.mark.asyncio
async def test_mock_provider_unavailable():
    provider = MockLLMProvider(name="test_mock", is_available_flag=False)
    assert provider.is_available() is False
    with pytest.raises(RuntimeError) as exc:
        await provider.generate([LLMMessage(role=MessageRole.USER, content="Hi")])
    assert "unavailable" in str(exc.value).lower()


def test_provider_status_reporting_unconfigured():
    # Gemini without API key
    gemini = GeminiProvider(api_key="")
    assert gemini.is_available() is False
    status = gemini.get_status()
    assert status.available is False
    assert "Missing" in status.message

    # OpenAI without API key
    openai = OpenAIProvider(name="openai", api_key="")
    assert openai.is_available() is False
    status_o = openai.get_status()
    assert status_o.available is False


def test_llm_router_registration_and_statuses():
    router = LLMRouter()
    statuses = router.list_statuses()
    names = [s.name for s in statuses]
    assert "gemini" in names
    assert "openai" in names
    assert "groq" in names
    assert "ollama" in names
    assert "mock" in names

    mock_prov = router.get_provider("mock")
    assert mock_prov.name == "mock"

    with pytest.raises(ValueError):
        router.get_provider("non_existent_provider")

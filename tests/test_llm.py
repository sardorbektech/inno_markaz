"""LLM Layer Unit Tests."""

import pytest
from app.config.llm_config import LLMConfig, OllamaConfig, OpenRouterConfig
from app.llm.factory import create_llm_provider
from app.llm.ollama import OllamaProvider
from app.llm.openrouter import OpenRouterProvider
from app.llm.provider import LLMMessage, LLMRequest, LLMResponse


def test_llm_provider_factory_ollama():
    cfg = LLMConfig(provider="ollama")
    provider = create_llm_provider(cfg)
    assert isinstance(provider, OllamaProvider)


def test_llm_provider_factory_openrouter():
    cfg = LLMConfig(provider="openrouter")
    provider = create_llm_provider(cfg)
    assert isinstance(provider, OpenRouterProvider)


def test_llm_request_structure():
    req = LLMRequest(
        messages=[LLMMessage(role="user", content="Salom")],
        temperature=0.0,
    )
    assert len(req.messages) == 1
    assert req.messages[0].role == "user"

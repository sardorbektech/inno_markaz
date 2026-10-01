"""LLM Configuration according to AGENTS.md Section 34."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from app.config.settings import settings


@dataclass
class OllamaConfig:
    base_url: str = settings.OLLAMA_BASE_URL
    model: str = settings.OLLAMA_MODEL
    temperature: float = 0.0


@dataclass
class OpenRouterConfig:
    api_key: str = settings.OPENROUTER_API_KEY
    base_url: str = settings.OPENROUTER_BASE_URL
    model: str = settings.OPENROUTER_MODEL
    temperature: float = 0.0


@dataclass
class GenerationConfig:
    max_tokens: int = 1024
    timeout_seconds: float = 120.0


@dataclass
class LLMConfig:
    provider: Literal["ollama", "openrouter"] = settings.LLM_PROVIDER
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    openrouter: OpenRouterConfig = field(default_factory=OpenRouterConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)


llm_config = LLMConfig()

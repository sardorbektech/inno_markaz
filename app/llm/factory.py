"""LLM Provider Factory according to AGENTS.md Section 33."""

from __future__ import annotations

from app.config.llm_config import LLMConfig, llm_config
from app.llm.ollama import OllamaProvider
from app.llm.openrouter import OpenRouterProvider
from app.llm.provider import LLMProvider


def create_llm_provider(config: LLMConfig | None = None) -> LLMProvider:
    """Creates and returns the configured LLMProvider instance."""
    cfg = config or llm_config
    if cfg.provider == "ollama":
        return OllamaProvider(cfg.ollama, cfg.generation)
    elif cfg.provider == "openrouter":
        return OpenRouterProvider(cfg.openrouter, cfg.generation)
    else:
        raise ValueError(f"Unknown LLM provider: {cfg.provider}. Expected 'ollama' or 'openrouter'.")

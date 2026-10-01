"""LLM Provider Interface and Data Models according to AGENTS.md Sections 0 and 33."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMMessage:
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMRequest:
    messages: list[LLMMessage]
    temperature: float = 0.0
    max_tokens: int = 5000
    model: str | None = None
    extra_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    tokens_used: dict[str, int] | None = None
    raw_response: dict[str, Any] | None = None


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""
    pass


class LLMTimeoutError(LLMProviderError):
    """Raised when LLM request times out."""
    pass


class LLMProvider(ABC):
    """Common Python LLM provider abstraction."""

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generates completion for the given request."""
        raise NotImplementedError

    @abstractmethod
    async def check_health(self) -> bool:
        """Verifies if the provider endpoint and model are reachable."""
        raise NotImplementedError

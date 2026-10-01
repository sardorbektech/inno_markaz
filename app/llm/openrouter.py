"""OpenRouter Provider Implementation."""

from __future__ import annotations

import httpx
from app.config.llm_config import OpenRouterConfig, GenerationConfig
from app.llm.provider import (
    LLMMessage,
    LLMProvider,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
    LLMTimeoutError,
)
from app.logging_config import logger


class OpenRouterProvider(LLMProvider):
    """Integrates with OpenRouter API."""

    def __init__(self, config: OpenRouterConfig, gen_config: GenerationConfig) -> None:
        self.config = config
        self.gen_config = gen_config
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "HTTP-Referer": "https://inno-markaz.uz",
            "X-Title": "Inno Markaz AI Agent",
            "Content-Type": "application/json",
        }
        self.client = httpx.AsyncClient(
            base_url=config.base_url.rstrip("/"),
            headers=headers,
            timeout=gen_config.timeout_seconds,
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.config.api_key:
            raise LLMProviderError("OpenRouter API key is not configured in .env")

        model = request.model or self.config.model
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens or self.gen_config.max_tokens,
        }

        try:
            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            choices = data.get("choices", [])
            content = choices[0].get("message", {}).get("content", "") if choices else ""
            usage = data.get("usage", {})

            return LLMResponse(
                content=content,
                model=model,
                provider="openrouter",
                tokens_used={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
                raw_response=data,
            )

        except httpx.TimeoutException as e:
            logger.error(f"OpenRouter request timed out after {self.gen_config.timeout_seconds}s")
            raise LLMTimeoutError(f"OpenRouter request timed out: {e}") from e
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter HTTP error {e.response.status_code}: {e.response.text}")
            raise LLMProviderError(f"OpenRouter HTTP error: {e.response.status_code}") from e
        except Exception as e:
            logger.error(f"OpenRouter request failed: {e}")
            raise LLMProviderError(f"OpenRouter request failed: {e}") from e

    async def check_health(self) -> bool:
        if not self.config.api_key:
            return False
        try:
            resp = await self.client.get("/models", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self.client.aclose()

"""Ollama Provider Implementation."""

from __future__ import annotations

import httpx
from app.config.llm_config import OllamaConfig, GenerationConfig
from app.llm.provider import (
    LLMMessage,
    LLMProvider,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
    LLMTimeoutError,
)
from app.logging_config import logger


class OllamaProvider(LLMProvider):
    """Integrates with locally running Ollama instance."""

    def __init__(self, config: OllamaConfig, gen_config: GenerationConfig) -> None:
        self.config = config
        self.gen_config = gen_config
        self.client = httpx.AsyncClient(
            base_url=config.base_url.rstrip("/"),
            timeout=gen_config.timeout_seconds,
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        model = request.model or self.config.model
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "stream": False,
            "think": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens or self.gen_config.max_tokens,
            },
        }

        try:
            response = await self.client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

            content = data.get("message", {}).get("content", "")
            tokens_used = {
                "prompt_eval_count": data.get("prompt_eval_count", 0),
                "eval_count": data.get("eval_count", 0),
            }

            return LLMResponse(
                content=content,
                model=model,
                provider="ollama",
                tokens_used=tokens_used,
                raw_response=data,
            )

        except httpx.TimeoutException as e:
            logger.error(f"Ollama request timed out after {self.gen_config.timeout_seconds}s")
            raise LLMTimeoutError(f"Ollama request timed out: {e}") from e
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error {e.response.status_code}: {e.response.text}")
            raise LLMProviderError(f"Ollama HTTP error: {e.response.status_code} - {e.response.text}") from e
        except Exception as e:
            logger.error(f"Ollama request failed: {e}")
            raise LLMProviderError(f"Ollama request failed: {e}") from e

    async def check_health(self) -> bool:
        try:
            resp = await self.client.get("/api/tags", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self.client.aclose()

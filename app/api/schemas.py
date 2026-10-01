"""Pydantic Request and Response Schemas."""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="Natural language question")
    user_role: str = Field(
        default="viewer",
        description="Role of the querying user (defaults to viewer)",
    )
    session_id: str | None = Field(default=None, description="Optional session ID for memory context")


class PipelineStage(BaseModel):
    stage: str
    status: str
    detail: str
    duration: str | None = Field(default=None, description="Duration in seconds, e.g. '0.25 s'")


class ChatResponse(BaseModel):
    success: bool = True
    answer: str
    sql: str | None = None
    query_plan: dict[str, Any] | None = None
    results: list[dict[str, Any]] | None = None
    row_count: int = 0
    execution_time_ms: float = 0.0
    request_id: str
    session_id: str | None = None
    stages: list[PipelineStage] = Field(default_factory=list)
    error: str | None = None
    error_code: str | None = None


class HealthResponse(BaseModel):
    status: str
    database: bool
    llm_provider: str
    model: str
    active_connections: int = 1


class ConfigResponse(BaseModel):
    app_name: str
    provider: str
    model: str
    environment: str

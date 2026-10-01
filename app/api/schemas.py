"""Pydantic Request and Response Schemas."""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="Natural language question")
    user_role: Literal["viewer", "analyst", "hr_admin", "superadmin"] = Field(
        default="analyst",
        description="Role of the querying user",
    )


class PipelineStage(BaseModel):
    stage: str
    status: str
    detail: str


class ChatResponse(BaseModel):
    success: bool = True
    answer: str
    sql: str | None = None
    query_plan: dict[str, Any] | None = None
    results: list[dict[str, Any]] | None = None
    row_count: int = 0
    execution_time_ms: float = 0.0
    request_id: str
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

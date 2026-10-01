"""FastAPI Routes for Inno Markaz AI Agent."""

from __future__ import annotations

import uuid
from typing import Any
from fastapi import APIRouter, HTTPException, status
from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    ConfigResponse,
    HealthResponse,
    PipelineStage,
)
from app.config.llm_config import llm_config
from app.config.settings import settings
from app.db.postgres import db_manager
from app.db.schema import get_compact_schema_context
from app.llm.service import llm_service
from app.logging_config import log_stage, logger
from app.mcp.authorization import AuthorizationError
from app.mcp.complexity_checker import QueryComplexityError
from app.mcp.executor import mcp_executor
from app.mcp.input_validator import InputValidationError
from app.mcp.parameterizer import ParameterizationError
from app.mcp.sensitivity_policy import SensitiveDataAccessDeniedError
from app.mcp.sql_ast_validator import SQLASTValidationError

router = APIRouter(prefix="/api", tags=["Agent"])


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """Processes natural language inquiry through the full MCP validation and PostgreSQL pipeline."""
    req_id = str(uuid.uuid4())
    log_stage("API", f"POST /api/chat received: '{request.message}' | Role: {request.user_role}", request_id=req_id)

    try:
        result = await mcp_executor.process_question(
            raw_question=request.message,
            user_role=request.user_role,
            request_id=req_id,
        )

        return ChatResponse(
            success=True,
            answer=result.answer,
            sql=result.sql,
            query_plan=result.query_plan,
            results=result.sanitized_results,
            row_count=result.row_count,
            execution_time_ms=result.execution_time_ms,
            request_id=result.request_id,
            stages=[PipelineStage(**s) for s in result.stages],
        )

    except InputValidationError as e:
        log_stage("ERROR", f"Input validation rejected: {e}", request_id=req_id)
        return ChatResponse(
            success=False,
            answer=str(e),
            error=str(e),
            error_code=e.code,
            request_id=req_id,
            stages=[PipelineStage(stage="INPUT_VALIDATION", status="rejected", detail=str(e))],
        )

    except AuthorizationError as e:
        log_stage("ERROR", f"Authorization rejected: {e}", request_id=req_id)
        return ChatResponse(
            success=False,
            answer=str(e),
            error=str(e),
            error_code=e.code,
            request_id=req_id,
            stages=[PipelineStage(stage="AUTHORIZATION", status="denied", detail=str(e))],
        )

    except SensitiveDataAccessDeniedError as e:
        log_stage("ERROR", f"Sensitivity policy rejected: {e}", request_id=req_id)
        return ChatResponse(
            success=False,
            answer=str(e),
            error=str(e),
            error_code=e.code,
            request_id=req_id,
            stages=[PipelineStage(stage="SENSITIVITY_POLICY", status="denied", detail=str(e))],
        )

    except QueryComplexityError as e:
        log_stage("ERROR", f"Complexity check rejected: {e}", request_id=req_id)
        return ChatResponse(
            success=False,
            answer=str(e),
            error=str(e),
            error_code=e.code,
            request_id=req_id,
            stages=[PipelineStage(stage="COMPLEXITY_CHECK", status="rejected", detail=str(e))],
        )

    except SQLASTValidationError as e:
        log_stage("ERROR", f"SQL AST validation rejected: {e}", request_id=req_id)
        return ChatResponse(
            success=False,
            answer=f"Xavfsizlik siyosati tufayli so'rov bekor qilindi: {e}",
            error=str(e),
            error_code=e.code,
            request_id=req_id,
            stages=[PipelineStage(stage="SQL_AST_VALIDATION", status="rejected", detail=str(e))],
        )

    except ParameterizationError as e:
        log_stage("ERROR", f"Parameterization failed: {e}", request_id=req_id)
        return ChatResponse(
            success=False,
            answer="So'rov parametrlarini qayta ishlashda xatolik yuz berdi.",
            error=str(e),
            error_code=e.code,
            request_id=req_id,
            stages=[PipelineStage(stage="PARAMETERIZATION", status="failed", detail=str(e))],
        )

    except TimeoutError as e:
        log_stage("ERROR", f"Operation timed out: {e}", request_id=req_id)
        return ChatResponse(
            success=False,
            answer="Ma'lumotlar bazasi so'rovi vaqti tugadi (Timeout). Iltimos, so'rovni soddalashtirib qayta urinib ko'ring.",
            error="Database query timeout",
            error_code="DATABASE_TIMEOUT",
            request_id=req_id,
            stages=[PipelineStage(stage="POSTGRESQL", status="timeout", detail=str(e))],
        )

    except Exception as e:
        logger.exception(f"Unhandled error in chat endpoint: {e}")
        log_stage("ERROR", f"Internal error: {type(e).__name__}", request_id=req_id)
        return ChatResponse(
            success=False,
            answer="Kutilmagan xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring.",
            error="Ichki server xatoligi",
            error_code="INTERNAL_ERROR",
            request_id=req_id,
            stages=[PipelineStage(stage="ERROR", status="failed", detail=type(e).__name__)],
        )


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Readiness and health check endpoint."""
    db_ok = await db_manager.check_health()
    active_model = (
        llm_config.ollama.model if llm_config.provider == "ollama" else llm_config.openrouter.model
    )

    return HealthResponse(
        status="healthy" if db_ok else "degraded",
        database=db_ok,
        llm_provider=llm_config.provider,
        model=active_model,
        active_connections=1 if db_ok else 0,
    )


@router.get("/config", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    """Returns safe runtime configuration."""
    active_model = (
        llm_config.ollama.model if llm_config.provider == "ollama" else llm_config.openrouter.model
    )
    return ConfigResponse(
        app_name=settings.APP_NAME,
        provider=llm_config.provider,
        model=active_model,
        environment=settings.APP_ENV,
    )


@router.get("/schema")
async def get_schema_meta() -> dict[str, Any]:
    """Returns compact schema context for UI inspection."""
    return get_compact_schema_context()

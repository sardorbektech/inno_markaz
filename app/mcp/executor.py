"""MCP Pipeline Executor coordinating all security and execution stages."""

from __future__ import annotations

import time
import uuid
from typing import Any
from app.db.postgres import db_manager
from app.db.schema import get_compact_schema_context
from app.llm.service import llm_service
from app.logging_config import log_stage
from app.mcp.authorization import authorization_manager
from app.mcp.complexity_checker import complexity_checker
from app.mcp.input_validator import validate_user_input
from app.mcp.parameterizer import parameterizer
from app.mcp.result_sanitizer import result_sanitizer
from app.mcp.schema_resolver import schema_resolver
from app.mcp.sensitivity_policy import sensitivity_policy
from app.mcp.sql_ast_validator import sql_ast_validator
from app.mcp.sql_generator import sql_generator


class MCPExecutionResult:
    """Holds the end-to-end outcome of an MCP pipeline execution."""

    def __init__(
        self,
        question: str,
        answer: str,
        sql: str,
        parameters: list[Any],
        query_plan: dict[str, Any],
        sanitized_results: list[dict[str, Any]],
        row_count: int,
        execution_time_ms: float,
        request_id: str,
        stages: list[dict[str, str]],
    ) -> None:
        self.question = question
        self.answer = answer
        self.sql = sql
        self.parameters = parameters
        self.query_plan = query_plan
        self.sanitized_results = sanitized_results
        self.row_count = row_count
        self.execution_time_ms = execution_time_ms
        self.request_id = request_id
        self.stages = stages


class MCPExecutor:
    """Orchestrates the entire MCP request pipeline according to AGENTS.md."""

    async def process_question(
        self,
        raw_question: str,
        user_role: str = "analyst",
        request_id: str | None = None,
    ) -> MCPExecutionResult:
        """Executes a natural language query through the full MCP security pipeline."""
        req_id = request_id or str(uuid.uuid4())
        start_time = time.perf_counter()
        stages: list[dict[str, str]] = []

        def record_stage(name: str, status: str, detail: str) -> None:
            stages.append({"stage": name, "status": status, "detail": detail})

        log_stage("USER", f"Question received: {raw_question}", request_id=req_id)
        record_stage("USER", "received", raw_question)

        # 1. Input Validation
        clean_question = validate_user_input(raw_question)
        record_stage("INPUT_VALIDATION", "passed", "Input clean and bounded")

        # 2. Schema Context Generation
        schema_ctx = get_compact_schema_context()

        # 3. LLM Query Planning
        query_plan = await llm_service.plan_query(clean_question, schema_ctx, request_id=req_id)
        record_stage("QUERY_PLAN", "generated", f"Intent: {query_plan.get('intent')}")

        # 4. Schema Resolution
        resolved_plan = schema_resolver.resolve_plan(clean_question, query_plan, request_id=req_id)
        record_stage("SCHEMA_RESOLUTION", "resolved", "Mapped natural language to schema")

        # 5. Authorization Check
        intent = resolved_plan.get("intent", "employee_count")
        authorization_manager.check_query_permission(intent, user_role=user_role, request_id=req_id)
        record_stage("AUTHORIZATION", "allowed", f"Role '{user_role}' authorized")

        # 6. SQL Generation & AST Validation
        # Generate safe SQL from plan
        raw_sql, params = sql_generator.generate_from_plan(resolved_plan, request_id=req_id)

        # Validate through AST Validator
        ast = sql_ast_validator.validate_and_parse(raw_sql, request_id=req_id)
        tables_used, columns_selected, is_aggregate = sql_ast_validator.extract_tables_and_columns(ast)
        record_stage("SQL_AST_VALIDATION", "approved", f"Tables: {list(tables_used)}")

        # 7. Data Sensitivity Check
        sensitivity_policy.check_sensitivity(
            tables_used,
            columns_selected,
            is_aggregate=is_aggregate,
            user_role=user_role,
            request_id=req_id,
        )
        record_stage("SENSITIVITY_POLICY", "approved", "No unauthorized sensitive fields")

        # 8. Query Complexity Check
        complexity_checker.check_ast_complexity(ast, request_id=req_id)
        record_stage("COMPLEXITY_CHECK", "passed", "Limits respected")

        # 9. Parameterization
        final_sql = raw_sql
        final_params = params
        record_stage("PARAMETERIZATION", "completed", f"{len(final_params)} parameters bound")

        # 10. PostgreSQL Execution
        raw_results, row_count, db_duration = await db_manager.execute_query(
            final_sql,
            final_params,
            request_id=req_id,
        )
        record_stage("POSTGRESQL", "executed", f"Returned {row_count} rows in {db_duration:.3f}s")

        # 11. Result Sanitization
        sanitized_results = result_sanitizer.sanitize(
            raw_results,
            user_role=user_role,
            request_id=req_id,
        )
        record_stage("RESULT_SANITIZER", "sanitized", f"{len(sanitized_results)} safe rows")

        # 12. Final Grounded Answer Generation
        answer = await llm_service.generate_answer(
            clean_question,
            resolved_plan,
            sanitized_results,
            row_count,
            request_id=req_id,
        )
        record_stage("LLM_ANSWER", "synthesized", "Direct grounded answer created")

        total_duration_ms = (time.perf_counter() - start_time) * 1000.0
        log_stage("RESPONSE", f"Pipeline completed in {total_duration_ms:.2f}ms", request_id=req_id)
        record_stage("RESPONSE", "completed", f"{total_duration_ms:.1f}ms")

        return MCPExecutionResult(
            question=clean_question,
            answer=answer,
            sql=final_sql,
            parameters=final_params,
            query_plan=resolved_plan,
            sanitized_results=sanitized_results,
            row_count=row_count,
            execution_time_ms=total_duration_ms,
            request_id=req_id,
            stages=stages,
        )


mcp_executor = MCPExecutor()

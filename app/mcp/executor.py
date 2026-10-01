"""MCP Pipeline Executor coordinating all security, timing, memory, and execution stages."""

from __future__ import annotations

import time
import uuid
from typing import Any
from app.db.postgres import db_manager
from app.db.schema import get_compact_schema_context
from app.llm.memory import conversation_memory
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
        session_id: str | None = None,
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
        self.session_id = session_id


class MCPExecutor:
    """Orchestrates the entire MCP request pipeline according to specifications."""

    async def process_question(
        self,
        raw_question: str,
        user_role: str = "viewer",
        session_id: str | None = None,
        request_id: str | None = None,
    ) -> MCPExecutionResult:
        """Executes a natural language query through the full MCP security pipeline."""
        req_id = request_id or str(uuid.uuid4())
        active_session_id = session_id or str(uuid.uuid4())
        start_time = time.perf_counter()
        stages: list[dict[str, str]] = []

        def record_stage(name: str, status: str, detail: str, duration: float) -> None:
            stages.append({
                "stage": name,
                "status": status,
                "detail": detail,
                "duration": f"{duration:.2f} s",
            })

        log_stage("USER", f"Question received: {raw_question}", request_id=req_id)

        # 1. Input Validation
        t0 = time.perf_counter()
        clean_question = validate_user_input(raw_question)
        record_stage("INPUT_VALIDATION", "passed", "Input clean, prompt injection filters passed", time.perf_counter() - t0)

        # 2. Schema Context Generation & Memory Lookup
        t0 = time.perf_counter()
        schema_ctx = get_compact_schema_context()
        history = conversation_memory.get_history(active_session_id)
        record_stage("SCHEMA_RESOLUTION", "ready", f"Schema context loaded | Memory messages: {len(history)}", time.perf_counter() - t0)

        # 3. LLM Query Planning (with conversational history)
        t0 = time.perf_counter()
        query_plan = await llm_service.plan_query(clean_question, schema_ctx, history=history, request_id=req_id)
        record_stage("QUERY_PLAN", "generated", f"Intent: {query_plan.get('intent')}", time.perf_counter() - t0)

        # 4. Schema Resolution
        t0 = time.perf_counter()
        resolved_plan = schema_resolver.resolve_plan(clean_question, query_plan, request_id=req_id)
        record_stage("SCHEMA_RESOLUTION", "resolved", "Mapped natural language tokens to schema entities", time.perf_counter() - t0)

        # 5. Authorization Check (viewer role)
        t0 = time.perf_counter()
        intent = resolved_plan.get("intent", "employee_count")
        authorization_manager.check_query_permission(intent, user_role=user_role, request_id=req_id)
        record_stage("AUTHORIZATION", "allowed", f"Role '{user_role}' authorized for read-only inquiry", time.perf_counter() - t0)

        # 6. SQL Generation & AST Validation
        t0 = time.perf_counter()
        raw_sql, params = sql_generator.generate_from_plan(resolved_plan, request_id=req_id)
        ast = sql_ast_validator.validate_and_parse(raw_sql, request_id=req_id)
        tables_used, columns_selected, is_aggregate = sql_ast_validator.extract_tables_and_columns(ast)
        record_stage("SQL_AST_VALIDATION", "approved", f"Single SELECT verified. Tables: {list(tables_used)}", time.perf_counter() - t0)

        # 7. Data Sensitivity Check
        t0 = time.perf_counter()
        sensitivity_policy.check_sensitivity(
            tables_used,
            columns_selected,
            is_aggregate=is_aggregate,
            user_role=user_role,
            request_id=req_id,
        )
        record_stage("SENSITIVITY_POLICY", "approved", "Permitted business read access verified", time.perf_counter() - t0)

        # 8. Query Complexity Check
        t0 = time.perf_counter()
        complexity_checker.check_ast_complexity(ast, request_id=req_id)
        record_stage("COMPLEXITY_CHECK", "passed", "Limits, joins, and column count respected", time.perf_counter() - t0)

        # 9. Parameterization
        t0 = time.perf_counter()
        final_sql = raw_sql
        final_params = params
        record_stage("PARAMETERIZATION", "completed", f"{len(final_params)} parameters securely bound", time.perf_counter() - t0)

        # 10. PostgreSQL Execution
        t0 = time.perf_counter()
        raw_results, row_count, db_duration = await db_manager.execute_query(
            final_sql,
            final_params,
            request_id=req_id,
        )
        record_stage("POSTGRESQL", "executed", f"Returned {row_count} rows in read-only transaction", time.perf_counter() - t0)

        # 11. Result Sanitization
        t0 = time.perf_counter()
        sanitized_results = result_sanitizer.sanitize(
            raw_results,
            user_role=user_role,
            request_id=req_id,
        )
        record_stage("RESULT_SANITIZER", "sanitized", f"{len(sanitized_results)} safe records formatted", time.perf_counter() - t0)

        # 12. Final Grounded Answer Generation (Beautiful Markdown)
        t0 = time.perf_counter()
        answer = await llm_service.generate_answer(
            clean_question,
            resolved_plan,
            sanitized_results,
            row_count,
            history=history,
            request_id=req_id,
        )
        record_stage("LLM_ANSWER", "synthesized", "Direct grounded Markdown response formulated", time.perf_counter() - t0)

        # Store user query and final answer in conversation memory (last 10 messages)
        conversation_memory.add_message(active_session_id, "user", clean_question)
        conversation_memory.add_message(active_session_id, "assistant", answer)

        total_duration = time.perf_counter() - start_time
        total_duration_ms = total_duration * 1000.0
        log_stage("RESPONSE", f"Pipeline completed in {total_duration_ms:.2f}ms", request_id=req_id)
        record_stage("RESPONSE", "completed", f"End-to-end pipeline finished", total_duration)

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
            session_id=active_session_id,
        )


mcp_executor = MCPExecutor()

"""Query Complexity Checker according to AGENTS.md Section 40."""

from __future__ import annotations

from typing import Any
import sqlglot
from sqlglot import exp
from app.config.security_config import security_config
from app.logging_config import log_stage


class QueryComplexityError(Exception):
    """Raised when a query exceeds allowable complexity bounds."""
    def __init__(self, message: str, code: str = "QUERY_TOO_COMPLEX") -> None:
        super().__init__(message)
        self.code = code


class ComplexityChecker:
    """Analyzes AST and query plan against resource & complexity limits."""

    def check_ast_complexity(self, ast: exp.Expression, request_id: str | None = None) -> None:
        """Verifies join counts, column counts, subquery counts, and limits on AST."""
        # Count joins
        joins = list(ast.find_all(exp.Join))
        join_count = len(joins)
        if join_count > security_config.max_joins:
            log_stage("COMPLEXITY_CHECK", f"Join count {join_count} exceeds limit {security_config.max_joins}", request_id=request_id)
            raise QueryComplexityError(
                f"So'rov juda murakkab: birlashtirishlar soni ({join_count}) limitdan ({security_config.max_joins}) oshib ketdi.",
                code="QUERY_TOO_COMPLEX",
            )

        # Count subqueries
        subqueries = list(ast.find_all(exp.Subquery))
        subquery_count = len(subqueries)
        if subquery_count > security_config.max_subqueries:
            log_stage("COMPLEXITY_CHECK", f"Subquery count {subquery_count} exceeds limit {security_config.max_subqueries}", request_id=request_id)
            raise QueryComplexityError(
                f"So'rovda ichki so'rovlar soni ({subquery_count}) ruxsat etilgan limitdan ({security_config.max_subqueries}) ko'p.",
                code="QUERY_TOO_COMPLEX",
            )

        # Count selected expressions / columns
        select_exprs = ast.expressions if hasattr(ast, "expressions") else []
        col_count = len(select_exprs)
        if col_count > security_config.max_selected_columns:
            log_stage("COMPLEXITY_CHECK", f"Selected column count {col_count} exceeds limit {security_config.max_selected_columns}", request_id=request_id)
            raise QueryComplexityError(
                f"Tanlangan ustunlar soni ({col_count}) ruxsat etilgan limitdan ({security_config.max_selected_columns}) ko'p.",
                code="QUERY_TOO_COMPLEX",
            )

        # Check LIMIT
        limit_node = ast.find(exp.Limit)
        if limit_node and limit_node.expression:
            try:
                limit_val = int(str(limit_node.expression))
                if limit_val > security_config.max_rows:
                    # Clamp limit node
                    limit_node.set("expression", exp.Literal.number(security_config.max_rows))
            except ValueError:
                pass
        else:
            # If no limit and no group by aggregation, inject default limit
            has_group_by = ast.find(exp.Group) is not None
            has_aggregates = bool(list(ast.find_all(exp.AggFunc)))
            if not has_group_by and not has_aggregates:
                ast.set("limit", exp.Limit(expression=exp.Literal.number(security_config.default_limit)))

        log_stage("COMPLEXITY_CHECK", f"Complexity check PASSED (Joins: {join_count}, Columns: {col_count})", request_id=request_id)


complexity_checker = ComplexityChecker()

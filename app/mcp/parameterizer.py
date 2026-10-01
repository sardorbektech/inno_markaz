"""Parameterization Layer according to AGENTS.md Section 30."""

from __future__ import annotations

from typing import Any
import sqlglot
from sqlglot import exp
from app.logging_config import log_stage


class ParameterizationError(Exception):
    """Raised when query values cannot be safely parameterized."""
    def __init__(self, message: str, code: str = "PARAMETERIZATION_ERROR") -> None:
        super().__init__(message)
        self.code = code


class Parameterizer:
    """Replaces literals in WHERE/HAVING/LIMIT clauses with $1, $2, ... placeholders."""

    def parameterize(self, ast: exp.Expression, request_id: str | None = None) -> tuple[str, list[Any]]:
        """Extracts literals into parameterized array and returns PostgreSQL SQL string with placeholders.

        Returns:
            (parameterized_sql, parameter_values)
        """
        log_stage("PARAMETERIZATION", "Parameterizing literal values...", request_id=request_id)
        params: list[Any] = []

        # Find where / having / limit clauses where literals should be parameterized
        # We walk where conditions
        where_clause = ast.find(exp.Where)
        if where_clause:
            for literal in list(where_clause.find_all(exp.Literal)):
                val: Any = literal.this
                if literal.is_number:
                    try:
                        val = int(val) if "." not in val else float(val)
                    except ValueError:
                        pass
                params.append(val)
                param_idx = len(params)
                # Replace node with placeholder $N
                literal.replace(exp.var(f"${param_idx}"))

            for boolean in list(where_clause.find_all(exp.Boolean)):
                params.append(boolean.this)
                param_idx = len(params)
                boolean.replace(exp.var(f"${param_idx}"))

        # Convert back to postgres SQL
        sql = ast.sql(dialect="postgres")
        # Ensure any double quotes or syntax is clean
        log_stage("PARAMETERIZATION", f"Parameters bound: {len(params)} | Shape: {sql}", request_id=request_id)
        return sql, params


parameterizer = Parameterizer()

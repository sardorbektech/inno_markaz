"""SQL AST Validator using sqlglot according to AGENTS.md Sections 26-29, 42."""

from __future__ import annotations

from typing import Any
import sqlglot
from sqlglot import exp
from app.config.security_config import security_config
from app.db.schema import (
    ALLOWED_TABLES,
    is_allowed_column,
    is_allowed_table,
)
from app.logging_config import log_stage


class SQLASTValidationError(Exception):
    """Raised when SQL AST fails security, grammar, or allowlist checks."""
    def __init__(self, message: str, code: str = "SQL_AST_REJECTED") -> None:
        super().__init__(message)
        self.code = code


class SQLASTValidator:
    """Performs deterministic AST analysis on all candidate SQL queries."""

    def validate_and_parse(self, sql: str, request_id: str | None = None) -> exp.Expression:
        """Parses and validates raw SQL query.

        Returns:
            The parsed sqlglot AST expression.
        Raises:
            SQLASTValidationError
        """
        log_stage("SQL_AST_VALIDATION", f"Parsing and validating SQL: {sql[:100]}...", request_id=request_id)

        # 1. Parse statement(s)
        try:
            expressions = sqlglot.parse(sql, read="postgres")
        except Exception as e:
            log_stage("SQL_AST_VALIDATION", f"SQL syntax error: {e}", request_id=request_id)
            raise SQLASTValidationError(f"SQL sintaksis xatosi: {e}", code="SQL_AST_REJECTED")

        # 2. Exactly one statement check
        if len(expressions) != 1:
            raise SQLASTValidationError(
                f"Faqat bitta SQL operatoriga ruxsat etilgan, ammo {len(expressions)} ta topildi.",
                code="SQL_AST_REJECTED",
            )

        ast = expressions[0]
        if ast is None:
            raise SQLASTValidationError("Bo'sh SQL so'rovi.", code="SQL_AST_REJECTED")

        # 3. Must be SELECT statement only
        if not isinstance(ast, exp.Select):
            raise SQLASTValidationError(
                f"Faqat SELECT so'rovlariga ruxsat etiladi. '{ast.key.upper()}' operatori qat'iyan taqiqlangan.",
                code="SQL_AST_REJECTED",
            )

        # 4. Check for forbidden operations / AST node types
        forbidden_nodes = (
            exp.Insert,
            exp.Update,
            exp.Delete,
            exp.Drop,
            exp.Create,
            exp.Alter,
            exp.Command,
        )
        for node in ast.walk():
            if isinstance(node, forbidden_nodes):
                raise SQLASTValidationError(
                    f"Taqiqlangan SQL konstruksiyasi aniqlandi: {type(node).__name__}",
                    code="SQL_AST_REJECTED",
                )

        # 5. Validate tables used (Allowlist)
        tables_used: set[str] = set()
        for tbl in ast.find_all(exp.Table):
            tbl_name = tbl.name.lower().strip('"')
            tables_used.add(tbl_name)
            if not is_allowed_table(tbl_name):
                log_stage("SQL_AST_VALIDATION", f"Forbidden table accessed: {tbl_name}", request_id=request_id)
                raise SQLASTValidationError(
                    f"Ruxsat etilmagan jadvalga murojaat qilindi: '{tbl_name}'. Faqat ruxsat etilgan jadvallardan foydalanish mumkin.",
                    code="SQL_AST_REJECTED",
                )

        # 6. Reject SELECT * (Section 42)
        for star in ast.find_all(exp.Star):
            # Check if this star is inside COUNT(*)
            parent = star.parent
            if isinstance(parent, exp.Count):
                continue
            raise SQLASTValidationError(
                "SELECT * dan foydalanish taqiqlangan. Faqat kerakli ustunlar aniq ko'rsatilishi shart.",
                code="SQL_AST_REJECTED",
            )

        # 7. Check for forbidden functions
        for func in ast.find_all(exp.Anonymous):
            func_name = func.name.lower()
            if func_name in security_config.forbidden_functions:
                raise SQLASTValidationError(
                    f"Taqiqlangan funksiya chaqiruvi: '{func_name}'",
                    code="SQL_AST_REJECTED",
                )

        # 8. Check known function nodes
        for func in ast.find_all(exp.Func):
            func_name = func.key.lower() if hasattr(func, "key") else ""
            if func_name in security_config.forbidden_functions:
                raise SQLASTValidationError(
                    f"Taqiqlangan funksiya chaqiruvi: '{func_name}'",
                    code="SQL_AST_REJECTED",
                )

        log_stage("SQL_AST_VALIDATION", f"AST validation PASSED. Tables used: {tables_used}", request_id=request_id)
        return ast

    def extract_tables_and_columns(self, ast: exp.Expression) -> tuple[set[str], set[str], bool]:
        """Extracts used tables, columns, and whether an aggregation function is used."""
        tables_used: set[str] = {t.name.lower().strip('"') for t in ast.find_all(exp.Table)}
        columns_selected: set[str] = set()

        for col in ast.find_all(exp.Column):
            columns_selected.add(col.name.lower().strip('"'))

        # Check for aggregation functions
        is_aggregate = bool(list(ast.find_all(exp.AggFunc))) or (ast.find(exp.Group) is not None)

        return tables_used, columns_selected, is_aggregate


sql_ast_validator = SQLASTValidator()

"""Unit Tests for MCP Components."""

import decimal
import pytest
from app.mcp.complexity_checker import QueryComplexityError, complexity_checker
from app.mcp.input_validator import InputValidationError, validate_user_input
from app.mcp.parameterizer import parameterizer
from app.mcp.result_sanitizer import result_sanitizer
from app.mcp.schema_resolver import schema_resolver
from app.mcp.sql_ast_validator import SQLASTValidationError, sql_ast_validator
from app.mcp.sql_generator import sql_generator


def test_input_validator_empty():
    with pytest.raises(InputValidationError):
        validate_user_input("   ")


def test_input_validator_null_byte():
    with pytest.raises(InputValidationError):
        validate_user_input("Test\x00Question")


def test_schema_resolver_uzbek_terms():
    plan = {
        "intent": "employee_count",
        "entities": {},
        "filters": [],
    }
    # Test work format: masofaviy -> Remote
    res = schema_resolver.resolve_plan("masofaviy ishlaydigan xodimlar", plan)
    assert res["entities"]["work_format"] == "Remote"

    # Test level: senior -> Senior
    res_level = schema_resolver.resolve_plan("Senior darajadagi xodimlar", plan)
    assert res_level["entities"]["position_level"] == "Senior"

    # Test status: faol -> Active + is_active = True
    res_active = schema_resolver.resolve_plan("faol xodimlar soni", plan)
    assert any(f.get("field") == "is_active" for f in res_active["filters"])


def test_ast_validator_disallows_select_star():
    with pytest.raises(SQLASTValidationError) as exc:
        sql_ast_validator.validate_and_parse("SELECT * FROM employees;")
    assert "SELECT *" in str(exc.value)


def test_ast_validator_allows_count_star():
    ast = sql_ast_validator.validate_and_parse("SELECT COUNT(*) AS total FROM employees;")
    assert ast is not None


def test_ast_validator_disallows_multiple_statements():
    with pytest.raises(SQLASTValidationError):
        sql_ast_validator.validate_and_parse("SELECT employee_id FROM employees; SELECT name FROM departments;")


def test_ast_validator_disallows_unknown_table():
    with pytest.raises(SQLASTValidationError) as exc:
        sql_ast_validator.validate_and_parse("SELECT id FROM users;")
    assert "users" in str(exc.value)


def test_parameterizer():
    ast = sql_ast_validator.validate_and_parse("SELECT first_name FROM employees WHERE work_format = 'Remote';")
    sql, params = parameterizer.parameterize(ast)
    assert "$1" in sql
    assert "Remote" in params


def test_result_sanitizer():
    raw_rows = [
        {
            "employee_id": "test01",
            "first_name": "Ali",
            "last_name": "Valiyev",
            "salary": decimal.Decimal("50000000.00"),
            "phone": "+998901234567",
        }
    ]
    # For analyst, salary and phone should be masked
    sanitized = result_sanitizer.sanitize(raw_rows, user_role="analyst")
    assert sanitized[0]["salary"] == "[PROTECTED]"
    assert sanitized[0]["phone"] == "[PROTECTED]"
    assert sanitized[0]["first_name"] == "Ali"


def test_complexity_checker_max_joins():
    ast = sql_ast_validator.validate_and_parse(
        """
        SELECT e.employee_id
        FROM employees e
        JOIN departments d ON d.department_id = e.department_id
        JOIN positions p ON p.position_id = e.position_id
        JOIN specialties s ON s.specialty_id = e.specialty_id
        JOIN employee_contacts c ON c.employee_id = e.employee_id
        JOIN employee_education ed ON ed.employee_id = e.employee_id
        JOIN departments d2 ON d2.department_id = e.department_id;
        """
    )
    with pytest.raises(QueryComplexityError):
        complexity_checker.check_ast_complexity(ast)

"""Tests for Employee Details & Similar Name Search, and Token limits."""

import pytest
from app.config.settings import settings
from app.config.llm_config import llm_config
from app.mcp.schema_resolver import schema_resolver
from app.mcp.sql_generator import sql_generator
from app.mcp.authorization import authorization_manager


def test_max_tokens_configuration():
    """Verify max_tokens is configured to 5000."""
    assert settings.LLM_MAX_TOKENS == 5000
    assert llm_config.generation.max_tokens == 5000


def test_schema_resolver_employee_details_exact():
    """Verify schema resolver resolves exact employee inquiry to employee_details."""
    question = "Rustam Ganiyev ma'lumotlarini bering"
    plan = {
        "intent": "unknown",
        "entities": {},
        "metrics": ["count"],
    }
    resolved = schema_resolver.resolve_plan(question, plan)
    assert resolved["intent"] == "employee_details"
    assert resolved["entities"]["first_name"] == "Rustam"
    assert resolved["entities"]["last_name"] == "Ganiyev"


def test_schema_resolver_employee_details_single_name():
    """Verify schema resolver handles single name inquiries."""
    question = "Rustam haqida ma'lumot bering"
    plan = {
        "intent": "unknown",
        "entities": {},
    }
    resolved = schema_resolver.resolve_plan(question, plan)
    assert resolved["intent"] == "employee_details"
    assert resolved["entities"]["first_name"] == "Rustam"


def test_sql_generator_employee_details_query():
    """Verify sql generator produces safe read-only SQL with fuzzy ordering."""
    plan = {
        "intent": "employee_details",
        "entities": {
            "first_name": "Rustam",
            "last_name": "Ganiyev",
        },
        "limit": 10,
    }
    sql, params = sql_generator.generate_from_plan(plan)
    assert "SELECT e.employee_id, e.first_name, e.last_name" in sql
    assert "e.first_name ILIKE $1" in sql
    assert "e.last_name ILIKE $2" in sql
    assert "ORDER BY" in sql
    assert "%Rustam%" in params
    assert "%Ganiyev%" in params


def test_authorization_viewer_employee_details():
    """Verify viewer role has permission to access employee details."""
    assert authorization_manager.check_query_permission("employee_details", user_role="viewer") is True

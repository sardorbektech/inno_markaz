"""Tests for PostgreSQL Database Layer."""

import pytest
from app.db.postgres import db_manager


@pytest.mark.asyncio
async def test_database_connection_and_health(db_connection):
    """Verifies that database pool connects and passes health check."""
    is_healthy = await db_manager.check_health()
    assert is_healthy is True


@pytest.mark.asyncio
async def test_database_read_only_execution(db_connection):
    """Verifies that read-only query executes correctly."""
    sql = "SELECT COUNT(*) AS total FROM employees;"
    rows, count, duration = await db_manager.execute_query(sql)
    assert count == 1
    assert "total" in rows[0]
    assert rows[0]["total"] > 0

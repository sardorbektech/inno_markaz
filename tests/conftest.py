"""Pytest fixtures and configuration for Inno Markaz test suite."""

import pytest
import pytest_asyncio
from app.db.postgres import db_manager


@pytest_asyncio.fixture(scope="function")
async def db_connection():
    """Initializes and tears down database connection pool for each test."""
    try:
        await db_manager.connect()
    except Exception as e:
        pytest.skip(f"Database not available for integration tests: {e}")
    yield db_manager
    await db_manager.disconnect()

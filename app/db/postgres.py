"""PostgreSQL Database Layer with asyncpg connection pooling.

Enforces read-only execution, timeout controls, and structured result extraction.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any
import asyncpg
from app.config.db_config import db_config
from app.config.security_config import security_config
from app.logging_config import log_stage, logger


class DatabaseManager:
    """Manages PostgreSQL connection pool and safe read-only query execution."""

    def __init__(self) -> None:
        self.pool: asyncpg.Pool | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    async def connect(self) -> None:
        """Initializes the connection pool for the currently running event loop."""
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if self.pool is not None:
            if self._loop == current_loop:
                return
            # If loop changed (e.g. during pytest runs), close old pool reference
            self.pool = None

        self._loop = current_loop
        try:
            self.pool = await asyncpg.create_pool(
                dsn=db_config.database_url,
                min_size=db_config.min_connections,
                max_size=db_config.max_connections,
                command_timeout=db_config.command_timeout_seconds,
            )
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    async def disconnect(self) -> None:
        """Closes the connection pool."""
        if self.pool is not None:
            try:
                await self.pool.close()
            except Exception:
                pass
            self.pool = None
            self._loop = None

    async def check_health(self) -> bool:
        """Checks if database is accessible."""
        try:
            try:
                current_loop = asyncio.get_running_loop()
            except RuntimeError:
                current_loop = None

            if self.pool is None or self._loop != current_loop:
                await self.connect()

            assert self.pool is not None
            async with self.pool.acquire() as conn:
                val = await conn.fetchval("SELECT 1;")
                return val == 1
        except Exception:
            return False

    async def execute_query(
        self,
        sql: str,
        parameters: list[Any] | None = None,
        request_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], int, float]:
        """Executes an approved, parameterized SQL query in a read-only transaction.

        Returns:
            (records, row_count, duration_seconds)
        """
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if self.pool is None or self._loop != current_loop:
            await self.connect()

        assert self.pool is not None
        params = parameters or []

        log_stage("POSTGRESQL", f"Executing approved read-only query: {sql} | Params: {params}", request_id=request_id)
        start_time = time.perf_counter()

        try:
            async with self.pool.acquire() as conn:
                timeout_ms = security_config.max_query_time_ms
                async with conn.transaction(readonly=True):
                    await conn.execute(f"SET LOCAL statement_timeout = '{timeout_ms}ms';")
                    rows = await conn.fetch(sql, *params)
                    duration = time.perf_counter() - start_time

                    results: list[dict[str, Any]] = [dict(row) for row in rows]
                    row_count = len(results)

                    log_stage(
                        "POSTGRESQL",
                        f"Query finished successfully in {duration:.4f}s | Rows returned: {row_count}",
                        request_id=request_id,
                    )
                    return results, row_count, duration

        except asyncio.TimeoutError:
            log_stage("ERROR", f"PostgreSQL query timed out after {security_config.max_query_time_ms}ms", request_id=request_id)
            raise TimeoutError("Database query timed out.")
        except Exception as e:
            log_stage("ERROR", f"PostgreSQL execution error: {e}", request_id=request_id)
            raise


db_manager = DatabaseManager()

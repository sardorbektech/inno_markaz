"""Database Configuration."""

from __future__ import annotations

from dataclasses import dataclass
from app.config.settings import settings


@dataclass
class DBConfig:
    database_url: str = settings.DATABASE_URL
    min_connections: int = 1
    max_connections: int = 10
    statement_timeout_seconds: float = 5.0
    command_timeout_seconds: float = 10.0


db_config = DBConfig()

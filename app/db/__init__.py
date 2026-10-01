"""Database package for Inno Markaz."""

from app.db.postgres import db_manager
from app.db.schema import (
    ALLOWED_TABLES,
    ALLOWED_POSITION_LEVELS,
    ALLOWED_EMPLOYMENT_STATUSES,
    ALLOWED_EMPLOYMENT_TYPES,
    ALLOWED_WORK_FORMATS,
    SCHEMA_TABLES,
    get_compact_schema_context,
)

__all__ = [
    "db_manager",
    "ALLOWED_TABLES",
    "ALLOWED_POSITION_LEVELS",
    "ALLOWED_EMPLOYMENT_STATUSES",
    "ALLOWED_EMPLOYMENT_TYPES",
    "ALLOWED_WORK_FORMATS",
    "SCHEMA_TABLES",
    "get_compact_schema_context",
]

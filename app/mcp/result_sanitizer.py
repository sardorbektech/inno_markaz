"""Result Sanitizer according to AGENTS.md Sections 31 and 32."""

from __future__ import annotations

import decimal
import datetime
from typing import Any
from app.config.security_config import security_config
from app.logging_config import log_stage
from app.mcp.authorization import authorization_manager


class ResultSanitizer:
    """Sanitizes raw PostgreSQL query results before exposing to the LLM or user."""

    # Disallowed columns for non-privileged users
    DISALLOWED_COLUMNS: set[str] = {
        "password",
        "hash",
        "secret",
        "token",
        "api_key",
        "contact_value",
    }

    def sanitize(
        self,
        raw_results: list[dict[str, Any]],
        user_role: str = "analyst",
        request_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Cleanses, normalizes, and filters raw records.

        Returns:
            Sanitized list of row dictionaries.
        """
        log_stage("RESULT_SANITIZER", f"Sanitizing {len(raw_results)} raw database records...", request_id=request_id)
        sanitized: list[dict[str, Any]] = []

        can_view_salary = authorization_manager.can_access_individual_salary(user_role)
        can_view_contacts = authorization_manager.can_access_personal_contacts(user_role)

        for row in raw_results[: security_config.max_rows]:
            clean_row: dict[str, Any] = {}
            for key, val in row.items():
                col_name = key.lower()

                # Block forbidden column names
                if col_name in self.DISALLOWED_COLUMNS and not can_view_contacts:
                    continue

                # Protect direct salary if not aggregate
                if col_name == "salary" and not can_view_salary:
                    # Individual salary is masked unless it's an aggregate (like avg_salary)
                    clean_row[key] = "[PROTECTED]"
                    continue

                # Protect personal phone and email for normal analytics
                if col_name in ("phone", "email") and not can_view_contacts:
                    clean_row[key] = "[PROTECTED]"
                    continue

                # Normalize datatypes
                if isinstance(val, (datetime.date, datetime.datetime)):
                    clean_row[key] = val.isoformat()
                elif isinstance(val, decimal.Decimal):
                    clean_row[key] = float(val)
                elif isinstance(val, str):
                    # Truncate overly long strings
                    clean_val = val[:500] if len(val) > 500 else val
                    # Neutralize potential prompt injection delimiters
                    clean_val = (
                        clean_val.replace("</DATABASE_RESULT>", "")
                        .replace("<USER_QUESTION>", "")
                        .replace("</USER_QUESTION>", "")
                    )
                    clean_row[key] = clean_val
                else:
                    clean_row[key] = val

            sanitized.append(clean_row)

        log_stage("RESULT_SANITIZER", f"Sanitization complete ({len(sanitized)} safe records)", request_id=request_id)
        return sanitized


result_sanitizer = ResultSanitizer()

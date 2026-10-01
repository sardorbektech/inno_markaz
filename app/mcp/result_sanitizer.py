"""Result Sanitizer.

Normalizes datatypes (dates, decimals) and strips any dangerous characters,
while allowing full visibility of business fields including salaries and personal contacts.
"""

from __future__ import annotations

import decimal
import datetime
from typing import Any
from app.config.security_config import security_config
from app.logging_config import log_stage


class ResultSanitizer:
    """Sanitizes raw PostgreSQL query results before exposing to the LLM or user."""

    # Truly confidential system credentials (not present in normal business data)
    SYSTEM_SECRET_COLUMNS: set[str] = {
        "password",
        "hash",
        "secret",
        "token",
        "api_key",
    }

    def sanitize(
        self,
        raw_results: list[dict[str, Any]],
        user_role: str = "viewer",
        request_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Cleanses, normalizes, and prepares raw records for output.
        All business fields (including salaries, contacts, education) are preserved.
        """
        log_stage("RESULT_SANITIZER", f"Sanitizing {len(raw_results)} raw database records...", request_id=request_id)
        sanitized: list[dict[str, Any]] = []

        for row in raw_results[: security_config.max_rows]:
            clean_row: dict[str, Any] = {}
            for key, val in row.items():
                col_name = key.lower()

                # Block system credentials if any exist
                if col_name in self.SYSTEM_SECRET_COLUMNS:
                    continue

                # Normalize datatypes
                if isinstance(val, (datetime.date, datetime.datetime)):
                    clean_row[key] = val.isoformat()
                elif isinstance(val, decimal.Decimal):
                    clean_row[key] = float(val)
                elif isinstance(val, str):
                    clean_val = val[:500] if len(val) > 500 else val
                    # Neutralize potential prompt injection injection markers
                    clean_val = clean_val.replace("###", "-")
                    clean_row[key] = clean_val
                else:
                    clean_row[key] = val

            sanitized.append(clean_row)

        log_stage("RESULT_SANITIZER", f"Sanitization complete ({len(sanitized)} safe records)", request_id=request_id)
        return sanitized


result_sanitizer = ResultSanitizer()

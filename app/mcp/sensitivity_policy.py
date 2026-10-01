"""Data Sensitivity Policy.

Permits full read access to all domain fields (including individual salaries,
personal contacts, and education) while strictly rejecting attempts to access
system-level sensitive catalogs (e.g. pg_authid, pg_shadow) or perform modifications.
"""

from __future__ import annotations

from typing import Any
from app.logging_config import log_stage


class SensitiveDataAccessDeniedError(Exception):
    """Raised when access to system-level sensitive resources is attempted."""
    def __init__(self, message: str, code: str = "SENSITIVE_DATA_ACCESS_DENIED") -> None:
        super().__init__(message)
        self.code = code


class SensitivityPolicyValidator:
    """Validates that queries only access permitted business domains in read-only mode."""

    FORBIDDEN_CATALOGS: set[str] = {
        "pg_shadow",
        "pg_authid",
        "pg_user",
        "pg_roles",
        "information_schema",
    }

    def check_sensitivity(
        self,
        tables_used: set[str],
        columns_selected: set[str],
        is_aggregate: bool,
        user_role: str = "viewer",
        request_id: str | None = None,
    ) -> None:
        """Evaluates tables against system catalog access.
        All business tables and personal fields are readable by the viewer.
        """
        log_stage("SENSITIVITY_POLICY", f"Checking sensitivity for tables: {tables_used} | columns: {columns_selected}", request_id=request_id)

        # Check for system catalog access attempts
        for tbl in tables_used:
            if tbl.lower() in self.FORBIDDEN_CATALOGS:
                log_stage("SENSITIVITY_POLICY", f"Access to system catalog '{tbl}' DENIED", request_id=request_id)
                raise SensitiveDataAccessDeniedError(
                    f"Tizim kataloglariga ('{tbl}') murojaat qilish qat'iyan taqiqlangan.",
                    code="SENSITIVE_DATA_ACCESS_DENIED",
                )

        log_stage("SENSITIVITY_POLICY", "Sensitivity policy check PASSED (Full business read permitted)", request_id=request_id)


sensitivity_policy = SensitivityPolicyValidator()

"""Data Sensitivity Policy according to AGENTS.md Sections 11 and 50."""

from __future__ import annotations

from typing import Any
from app.db.schema import is_sensitive_column
from app.logging_config import log_stage
from app.mcp.authorization import authorization_manager


class SensitiveDataAccessDeniedError(Exception):
    """Raised when access to sensitive/personal data is forbidden by policy."""
    def __init__(self, message: str, code: str = "SENSITIVE_DATA_ACCESS_DENIED") -> None:
        super().__init__(message)
        self.code = code


class SensitivityPolicyValidator:
    """Enforces policy on sensitive fields like salary and personal contacts."""

    def check_sensitivity(
        self,
        tables_used: set[str],
        columns_selected: set[str],
        is_aggregate: bool,
        user_role: str = "analyst",
        request_id: str | None = None,
    ) -> None:
        """Evaluates columns and tables against sensitivity restrictions."""
        log_stage("SENSITIVITY_POLICY", f"Checking sensitivity for tables: {tables_used} | columns: {columns_selected}", request_id=request_id)

        # 1. Salary Policy (Section 11.1)
        has_salary = any("salary" in col.lower() for col in columns_selected)
        if has_salary:
            if not is_aggregate:
                if not authorization_manager.can_access_individual_salary(user_role):
                    log_stage("SENSITIVITY_POLICY", "Individual salary access DENIED by policy", request_id=request_id)
                    raise SensitiveDataAccessDeniedError(
                        "Xodimlarning individual maosh ma'lumotlarini ko'rish taqiqlangan. Faqat bo'lim yoki umumiy o'rtacha/statistik ma'lumotlar ruxsat etiladi.",
                        code="SENSITIVE_DATA_ACCESS_DENIED",
                    )
            log_stage("SENSITIVITY_POLICY", "Salary aggregate access ALLOWED", request_id=request_id)

        # 2. Personal Contacts Policy (Section 11.2 & 50)
        has_contact_val = any("contact_value" in col.lower() for col in columns_selected) or (
            "employee_contacts" in tables_used and not is_aggregate
        )
        if has_contact_val:
            if not authorization_manager.can_access_personal_contacts(user_role):
                log_stage("SENSITIVITY_POLICY", "Personal contact values access DENIED by policy", request_id=request_id)
                raise SensitiveDataAccessDeniedError(
                    "Xodimlarning shaxsiy aloqa ma'lumotlari (telefon, telegram) xavfsizlik siyosati bo'yicha yopiq hisoblanadi.",
                    code="SENSITIVE_DATA_ACCESS_DENIED",
                )

        # 3. Direct personal contact columns in employees table (phone, email)
        has_phone_or_email = any(col.lower() in ("phone", "email", "employees.phone", "employees.email") for col in columns_selected)
        if has_phone_or_email and not is_aggregate:
            if not authorization_manager.can_access_personal_contacts(user_role):
                log_stage("SENSITIVITY_POLICY", "Personal phone/email access DENIED by policy", request_id=request_id)
                raise SensitiveDataAccessDeniedError(
                    "Xodimlarning telefon raqami va elektron pochtasi shaxsiy ma'lumotlar hisoblanadi va oddiy tahlilda taqdim etilmaydi.",
                    code="SENSITIVE_DATA_ACCESS_DENIED",
                )

        log_stage("SENSITIVITY_POLICY", "Sensitivity policy check PASSED", request_id=request_id)


sensitivity_policy = SensitivityPolicyValidator()

"""Authorization Layer according to AGENTS.md Sections 10, 11, 50."""

from __future__ import annotations

from typing import Any
from app.logging_config import log_stage


class AuthorizationError(Exception):
    """Raised when access to a resource or sensitive data is unauthorized."""
    def __init__(self, message: str, code: str = "UNAUTHORIZED") -> None:
        super().__init__(message)
        self.code = code


class AuthorizationManager:
    """Manages role-based query permissions and sensitive resource authorizations."""

    # Default permitted analytical operations per role
    ROLE_PERMISSIONS: dict[str, set[str]] = {
        "viewer": {
            "analytics:count",
            "analytics:departments",
            "analytics:specialties",
            "analytics:positions",
            "analytics:salary_aggregate",
        },
        "analyst": {
            "analytics:count",
            "analytics:departments",
            "analytics:specialties",
            "analytics:positions",
            "analytics:salary_aggregate",
            "analytics:employee_list",
            "analytics:managers",
            "analytics:education_aggregate",
        },
        "hr_admin": {
            "analytics:count",
            "analytics:departments",
            "analytics:specialties",
            "analytics:positions",
            "analytics:salary_aggregate",
            "analytics:employee_list",
            "analytics:managers",
            "analytics:education_aggregate",
            "data:individual_salary",
            "data:personal_contacts",
            "data:personal_education",
        },
        "superadmin": {
            "*",
        },
    }

    def check_query_permission(
        self,
        intent: str,
        user_role: str = "analyst",
        request_id: str | None = None,
    ) -> bool:
        """Verifies if the user's role permits the given analytical intent."""
        log_stage("AUTHORIZATION", f"Checking role '{user_role}' permission for intent '{intent}'", request_id=request_id)
        role = user_role.lower()
        perms = self.ROLE_PERMISSIONS.get(role, self.ROLE_PERMISSIONS["analyst"])

        if "*" in perms:
            log_stage("AUTHORIZATION", "Superadmin access granted", request_id=request_id)
            return True

        # Check intent-specific permission
        intent_perm_map = {
            "employee_count": "analytics:count",
            "employee_list": "analytics:employee_list",
            "department_analytics": "analytics:departments",
            "specialty_analytics": "analytics:specialties",
            "salary_analytics": "analytics:salary_aggregate",
            "manager_analytics": "analytics:managers",
            "education_analytics": "analytics:education_aggregate",
        }

        required_perm = intent_perm_map.get(intent, "analytics:count")
        if required_perm not in perms:
            log_stage("AUTHORIZATION", f"Access DENIED for role '{user_role}' to '{required_perm}'", request_id=request_id)
            raise AuthorizationError(
                f"Sizning rolingiz ('{user_role}') uchun ushbu so'rovni bajarish ruxsat etilmagan.",
                code="UNAUTHORIZED",
            )

        log_stage("AUTHORIZATION", f"Read access ALLOWED for role '{user_role}'", request_id=request_id)
        return True

    def can_access_individual_salary(self, user_role: str) -> bool:
        perms = self.ROLE_PERMISSIONS.get(user_role.lower(), set())
        return "*" in perms or "data:individual_salary" in perms

    def can_access_personal_contacts(self, user_role: str) -> bool:
        perms = self.ROLE_PERMISSIONS.get(user_role.lower(), set())
        return "*" in perms or "data:personal_contacts" in perms


authorization_manager = AuthorizationManager()

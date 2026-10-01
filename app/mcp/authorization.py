"""Authorization Layer.

Enforces single-role 'viewer' with full read permissions for all database entities,
including personal contacts and individual salary, while strictly forbidding any write or DDL operations.
"""

from __future__ import annotations

from typing import Any
from app.logging_config import log_stage


class AuthorizationError(Exception):
    """Raised when access to a resource or operation is unauthorized."""
    def __init__(self, message: str, code: str = "UNAUTHORIZED") -> None:
        super().__init__(message)
        self.code = code


class AuthorizationManager:
    """Manages authorizations for the single 'viewer' read-only role."""

    def check_query_permission(
        self,
        intent: str,
        user_role: str = "viewer",
        request_id: str | None = None,
    ) -> bool:
        """Verifies if the viewer role permits the given analytical or read intent."""
        log_stage("AUTHORIZATION", f"Checking role '{user_role}' permission for intent '{intent}'", request_id=request_id)

        # Block any non-read intents immediately
        forbidden_intents = {"insert", "update", "delete", "drop", "alter", "create", "truncate", "grant", "revoke"}
        if intent.lower() in forbidden_intents:
            log_stage("AUTHORIZATION", f"Write intent '{intent}' DENIED by read-only policy", request_id=request_id)
            raise AuthorizationError(
                "Faqat o'qish (read-only) rejimiga ruxsat etilgan. Ma'lumotlarni o'zgartirish taqiqlangan.",
                code="UNAUTHORIZED",
            )

        log_stage("AUTHORIZATION", f"Read access ALLOWED for role '{user_role}'", request_id=request_id)
        return True

    def can_access_individual_salary(self, user_role: str = "viewer") -> bool:
        """Viewer role has full permission to inspect any salary information."""
        return True

    def can_access_personal_contacts(self, user_role: str = "viewer") -> bool:
        """Viewer role has full permission to inspect personal contact information."""
        return True


authorization_manager = AuthorizationManager()

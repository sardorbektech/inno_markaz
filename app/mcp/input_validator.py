"""Input Validation and Sanitization according to AGENTS.md."""

from __future__ import annotations

import re
from app.config.security_config import security_config


class InputValidationError(Exception):
    """Raised when user input violates validation policy."""
    def __init__(self, message: str, code: str = "INVALID_INPUT") -> None:
        super().__init__(message)
        self.code = code


def validate_user_input(question: str) -> str:
    """Validates and sanitizes raw user question.

    Returns:
        Sanitized clean string.
    Raises:
        InputValidationError
    """
    if not question or not question.strip():
        raise InputValidationError("Savol bo'sh bo'lishi mumkin emas (Question cannot be empty).", code="INVALID_INPUT")

    # Check length
    if len(question) > security_config.max_input_length:
        raise InputValidationError(
            f"Savol uzunligi ruxsat etilgan me'yordan oshib ketdi (maksimal {security_config.max_input_length} ta belgi).",
            code="INVALID_INPUT",
        )

    # Check for null bytes
    if "\x00" in question:
        raise InputValidationError("Kiritilgan matnda nojo'ya belgilar mavjud.", code="INVALID_INPUT")

    sanitized = question.strip()

    # Block direct destructive SQL injection patterns in question
    destructive_patterns = [
        r"\bDROP\s+TABLE\b",
        r"\bTRUNCATE\s+TABLE\b",
        r"\bDELETE\s+FROM\b",
        r"\bALTER\s+TABLE\b",
        r"\bGRANT\s+ALL\b",
        r"\bREVOKE\s+ALL\b",
    ]
    for pattern in destructive_patterns:
        if re.search(pattern, sanitized, re.IGNORECASE):
            raise InputValidationError(
                "Tizim faqat o'qish (read-only) rejimida ishlaydi. Ma'lumotlarni o'chirish yoki o'zgartirish taqiqlangan.",
                code="POLICY_VIOLATION",
            )

    return sanitized

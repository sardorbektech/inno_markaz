"""Input Validation and Prompt Injection Defense Layer."""

from __future__ import annotations

import re
from app.config.security_config import security_config


class InputValidationError(Exception):
    """Raised when user input violates validation policy or security rules."""
    def __init__(self, message: str, code: str = "INVALID_INPUT") -> None:
        super().__init__(message)
        self.code = code


def validate_user_input(question: str) -> str:
    """Validates, sanitizes, and inspects user inquiries against prompt and SQL injections.

    Returns:
        Clean, verified question string.
    Raises:
        InputValidationError
    """
    if not question or not question.strip():
        raise InputValidationError("Savol bo'sh bo'lishi mumkin emas.", code="INVALID_INPUT")

    # 1. Enforce length limits
    if len(question) > security_config.max_input_length:
        raise InputValidationError(
            f"Savol uzunligi ruxsat etilgan me'yordan oshib ketdi (maksimal {security_config.max_input_length} ta belgi).",
            code="INVALID_INPUT",
        )

    # 2. Reject null bytes and binary control characters
    if "\x00" in question or any(ord(c) < 32 and c not in "\n\r\t" for c in question):
        raise InputValidationError("Kiritilgan matnda nojo'ya yoki xavfli belgilar mavjud.", code="INVALID_INPUT")

    sanitized = question.strip()

    # 3. Detect and reject pseudo-system and tag injection attempts
    tag_injection_patterns = [
        r"<\s*/?\s*(?:user|system|assistant|prompt|context|schema|admin|instruction)[^>]*>",
    ]
    for pattern in tag_injection_patterns:
        if re.search(pattern, sanitized, re.IGNORECASE):
            raise InputValidationError(
                "Xavfsizlik siyosati: Tizim teglari (<USER>, <SYSTEM> va h.k.) orqali kiritish taqiqlangan.",
                code="POLICY_VIOLATION",
            )

    # 4. Detect and reject direct prompt injection / jailbreak patterns
    prompt_injection_patterns = [
        r"\bignore\s+(?:all\s+)?(?:previous\s+)?instructions\b",
        r"\bdisregard\s+(?:all\s+)?(?:previous\s+)?rules\b",
        r"\bforget\s+(?:all\s+)?(?:prior\s+)?rules\b",
        r"\byou\s+are\s+now\b",
        r"\bact\s+as\s+(?:an?\s+)?(?:unrestricted|evil|admin|root)\b",
        r"\bjailbreak\b",
        r"\bdan\s+mode\b",
        r"\breveal\s+(?:your\s+)?(?:system\s+)?prompt\b",
        r"\bshow\s+(?:your\s+)?(?:system\s+)?instructions\b",
    ]
    for pattern in prompt_injection_patterns:
        if re.search(pattern, sanitized, re.IGNORECASE):
            raise InputValidationError(
                "Xavfsizlik siyosati: Tizim yo'riqnomalarini chetlab o'tish (Prompt Injection) aniqlandi va so'rov bekor qilindi.",
                code="POLICY_VIOLATION",
            )

    # 5. Block destructive DDL / DML and stacked injection attempts
    destructive_sql_patterns = [
        r"\bDROP\s+TABLE\b",
        r"\bTRUNCATE\s+TABLE\b",
        r"\bDELETE\s+FROM\b",
        r"\bALTER\s+TABLE\b",
        r"\bGRANT\s+ALL\b",
        r"\bREVOKE\s+ALL\b",
        r"\bINSERT\s+INTO\b",
        r"\bUPDATE\s+[a-zA-Z_]+\s+SET\b",
        r";\s*--",
        r";\s*DROP\b",
        r";\s*DELETE\b",
    ]
    for pattern in destructive_sql_patterns:
        if re.search(pattern, sanitized, re.IGNORECASE):
            raise InputValidationError(
                "Tizim faqat o'qish (read-only) rejimida ishlaydi. Ma'lumotlarni o'chirish, qo'shish yoki o'zgartirish qat'iyan taqiqlangan.",
                code="POLICY_VIOLATION",
            )

    return sanitized

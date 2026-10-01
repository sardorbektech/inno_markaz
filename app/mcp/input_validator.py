"""Input Validation and Prompt Injection Defense Layer."""

from __future__ import annotations

import re
from app.config.security_config import security_config


class InputValidationError(Exception):
    """Raised when user input violates validation policy or security rules."""
    def __init__(self, message: str, code: str = "INVALID_INPUT") -> None:
        super().__init__(message)
        self.code = code


def normalize_for_injection_check(text: str) -> str:
    """Normalizes text to detect obfuscated prompt injections and leetspeak bypasses.

    Examples:
        'i.g.n.o.r.e a.l.l r.u.l.e.s' -> 'ignore all rules'
        'j-a-i-l-b-r-e-a-k' -> 'jailbreak'
        'i g n o r e' -> 'ignore'
    """
    # 1. Strip punctuation dots, hyphens, underscores between letters
    cleaned = re.sub(r"(?<=[a-zA-Zа-яА-Яo'g'shchO'G'SHCH])[.\-_/\\*+](?=[a-zA-Zа-яА-Яo'g'shchO'G'SHCH])", "", text)
    # 2. Collapse sequences of single separated letters (e.g. 'i g n o r e' -> 'ignore')
    cleaned = re.sub(r"\b([a-zA-Zа-яА-Я])\s+(?=[a-zA-Zа-яА-Я]\b)", r"\1", cleaned)
    return cleaned


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
    normalized = normalize_for_injection_check(sanitized)

    # 3. Detect and reject XML/HTML-like tags (pseudo-system tags, security override tags, etc.)
    # Allows comparison symbols like "maosh > 5000000" or "tajriba < 5", but rejects tags "<tag ...>" or "</tag>"
    tag_injection_patterns = [
        r"<\s*/?\s*[a-zA-Z_][a-zA-Z0-9_\-\:]*(?:\s+[^>]*)?>",
    ]
    for pattern in tag_injection_patterns:
        if re.search(pattern, sanitized, re.IGNORECASE):
            raise InputValidationError(
                "Xavfsizlik siyosati: Tizim teglari (<USER>, <security_override> va h.k.) orqali kiritish taqiqlangan.",
                code="POLICY_VIOLATION",
            )

    # 4. Detect and reject direct & obfuscated prompt injection / jailbreak patterns (English, Uzbek, Russian)
    prompt_injection_patterns = [
        # English jailbreak & override patterns
        r"\bignore\s+(?:all\s+)?(?:previous\s+)?(?:instructions|rules)\b",
        r"\bdisregard\s+(?:all\s+)?(?:previous\s+)?(?:rules|instructions)\b",
        r"\bforget\s+(?:all\s+)?(?:prior|previous\s+)?(?:rules|instructions)\b",
        r"\byou\s+are\s+now\b",
        r"\bact\s+as\s+(?:an?\s+)?(?:unrestricted|evil|admin|root)\b",
        r"\bjailbreak\b",
        r"\bdan\s+mode\b",
        r"\breveal\s+(?:your\s+)?(?:system\s+)?prompt\b",
        r"\bshow\s+(?:your\s+)?(?:system\s+)?instructions\b",
        r"\bbypass\s+(?:all\s+)?(?:security|rules|filters)\b",
        r"\bunrestricted\s+mode\b",
        r"\bdeveloper\s+mode\b",
        r"\b(?:print|show|reveal|give\s+me)\s+(?:the\s+)?(?:secret\s+)?(?:password|passwords|credentials)\b",
        r"\bQUERY_PLANNER_SYSTEM_PROMPT\b",
        r"\bANSWER_GENERATOR_SYSTEM_PROMPT\b",

        # Uzbek jailbreak & override patterns
        r"\b(?:avvalgi|barcha|oldingi)\s+(?:barcha\s+)?(?:ko'rsatma|qoida|yo'riqnoma|cheklov)(?:lar)?(?:ni)?\s+(?:bekor\s+qil|unut|tashla|e'tiborsiz\s+qoldir)\b",
        r"\b(?:qoidalar|ko'rsatmalar|yo'riqnomalar)(?:ni)?\s+(?:unut|bekor\s+qil|chetlab\s+o't)\b",
        r"\bsen\s+endi\s+(?:erkin|cheklanmagan|admin|boshqa)\b",
        r"\b(?:tizim|system)\s+(?:yo'riqnoma|prompt|buyruq|ko'rsatma)(?:lar)?(?:ini)?\s+(?:to'liq\s+)?(?:ko'rsat|ayt|ochiqla|ber)\b",
        r"\btizim(?:ning)?\s+(?:ichki\s+)?(?:yo'riqnoma|prompt)(?:lar)?(?:ini)?\b",
        r"\b(?:barcha\s+)?tizim\s+sirlari(?:ni)?\b",

        # Russian jailbreak & override patterns
        r"\b(?:игнорируй|забудь|отмени)\s+(?:все\s+)?(?:предыдущие\s+)?(?:правила|инструкции|ограничения)\b",
        r"\bты\s+теперь\s+(?:свободный|администратор|evil|без\s+ограничений)\b",
        r"\b(?:покажи|раскрой|выведи)\s+(?:мне\s+)?(?:системный\s+)?(?:промпт|инструкции|правила)\b",
        r"\bсистемный\s+промпт\b",
        r"\bсними\s+все\s+ограничения\b",
    ]
    for pattern in prompt_injection_patterns:
        if re.search(pattern, sanitized, re.IGNORECASE) or re.search(pattern, normalized, re.IGNORECASE):
            raise InputValidationError(
                "Xavfsizlik siyosati: Tizim yo'riqnomalarini chetlab o'tish (Prompt Injection) aniqlandi va so'rov bekor qilindi.",
                code="POLICY_VIOLATION",
            )

    # 5. Detect and reject attempts to query system catalogs and forbidden metadata tables
    system_catalog_patterns = [
        r"\bpg_shadow\b",
        r"\bpg_authid\b",
        r"\bpg_user\b",
        r"\bpg_roles\b",
        r"\bpg_catalog\b",
        r"\bpg_tables\b",
        r"\binformation_schema\b",
        r"\bsys\.tables\b",
        r"\bsqlite_master\b",
    ]
    for pattern in system_catalog_patterns:
        if re.search(pattern, sanitized, re.IGNORECASE) or re.search(pattern, normalized, re.IGNORECASE):
            raise InputValidationError(
                "Xavfsizlik siyosati: Tizim kataloglari va metama'lumotlarga (pg_shadow, information_schema va h.k.) kirish qat'iyan taqiqlangan.",
                code="POLICY_VIOLATION",
            )

    # 6. Block destructive DDL / DML, stacked injection, and classical SQL injection signatures
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
        r";\s*INSERT\b",
        r";\s*UPDATE\b",
        r";\s*SELECT\b",
        r"\bUNION\s+(?:ALL\s+)?SELECT\b",
        r"'\s*(?:OR|AND)\s+['\"0-9]",
        r"'\s*OR\s+'?1'?\s*=\s*'?1'?",
        r"/\*.*?\*/",
    ]
    for pattern in destructive_sql_patterns:
        if re.search(pattern, sanitized, re.IGNORECASE) or re.search(pattern, normalized, re.IGNORECASE):
            raise InputValidationError(
                "Tizim faqat o'qish (read-only) rejimida ishlaydi. Ma'lumotlarni o'chirish, qo'shish yoki o'zgartirish qat'iyan taqiqlangan.",
                code="POLICY_VIOLATION",
            )

    return sanitized

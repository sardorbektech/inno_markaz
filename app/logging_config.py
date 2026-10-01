"""Terminal Logging and Process Visibility Configuration for Inno Markaz.

Conforms to AGENTS.md requirements for terminal visibility and correlation tracing.
"""

from __future__ import annotations

import logging
import re
import sys
from typing import Any

# Color codes for terminal visibility
COLORS = {
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
    "DIM": "\033[2m",
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "BLUE": "\033[94m",
    "MAGENTA": "\033[95m",
    "CYAN": "\033[96m",
    "WHITE": "\033[97m",
    "STAGE": "\033[1;36m",  # Bold Cyan
}

STAGE_COLORS = {
    "USER": "\033[1;97m",       # Bold White
    "API": "\033[1;34m",        # Bold Blue
    "LLM": "\033[1;35m",        # Bold Magenta
    "QUERY_PLAN": "\033[1;33m", # Bold Yellow
    "MCP": "\033[1;36m",        # Bold Cyan
    "SCHEMA_RESOLUTION": "\033[36m",
    "AUTHORIZATION": "\033[32m",
    "SENSITIVITY_POLICY": "\033[33m",
    "COMPLEXITY_CHECK": "\033[34m",
    "SQL_GENERATION": "\033[35m",
    "SQL_AST_VALIDATION": "\033[1;32m",
    "PARAMETERIZATION": "\033[34m",
    "POSTGRESQL": "\033[1;33m",
    "RESULT_SANITIZER": "\033[32m",
    "LLM_ANSWER": "\033[1;35m",
    "RESPONSE": "\033[1;92m",
    "ERROR": "\033[1;91m",
}


class SecretMaskingFilter(logging.Filter):
    """Masks database passwords, API keys, tokens, and authorization headers."""

    # Regex patterns for sensitive credentials
    PATTERNS = [
        (re.compile(r"postgresql://([^:]+):([^@]+)@", re.IGNORECASE), r"postgresql://\1:***@"),
        (re.compile(r"(api[_-]?key\s*[:=]\s*['\"]?)([^'\";\s]+)", re.IGNORECASE), r"\1***"),
        (re.compile(r"(bearer\s+)([A-Za-z0-9\-._~+/]+=*)", re.IGNORECASE), r"\1***"),
        (re.compile(r"(password\s*[:=]\s*['\"]?)([^'\";\s]+)", re.IGNORECASE), r"\1***"),
        (re.compile(r"(sk-[a-zA-Z0-9_\-]{10,})", re.IGNORECASE), r"sk-***"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, repl in self.PATTERNS:
                record.msg = pattern.sub(repl, record.msg)
        return True


class StageFormatter(logging.Formatter):
    """Custom formatter for stage-based terminal logging."""

    def format(self, record: logging.LogRecord) -> str:
        req_id = getattr(record, "request_id", "")
        stage = getattr(record, "stage", None)
        req_prefix = f"[{req_id[:8]}] " if req_id else ""

        stage_color = STAGE_COLORS.get(stage, COLORS["STAGE"]) if stage else ""
        reset = COLORS["RESET"]

        if stage:
            header = f"{stage_color}[{stage}]{reset}"
            return f"{req_prefix}{header} {record.getMessage()}"
        else:
            return f"{req_prefix}[{record.levelname}] {record.getMessage()}"


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configures application-wide logging."""
    logger = logging.getLogger("inno_markaz")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    handler.setFormatter(StageFormatter())
    handler.addFilter(SecretMaskingFilter())

    logger.addHandler(handler)
    logger.propagate = False
    return logger


logger = setup_logging()


def log_stage(stage: str, message: str, request_id: str | None = None, **extra: Any) -> None:
    """Helper to log a specific architecture stage with request correlation."""
    extra_dict: dict[str, Any] = {"stage": stage}
    if request_id:
        extra_dict["request_id"] = request_id
    extra_dict.update(extra)
    logger.info(message, extra=extra_dict)

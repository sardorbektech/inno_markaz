"""Security and Policy Configuration according to AGENTS.md Section 40."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SecurityConfig:
    max_rows: int = 1000
    default_limit: int = 10
    max_joins: int = 5
    max_selected_columns: int = 30
    max_query_time_ms: int = 5000
    max_result_bytes: int = 1_000_000
    max_subqueries: int = 2
    max_ast_depth: int = 10
    max_input_length: int = 1000

    # Allowed SQL operations
    allowed_statements: list[str] = field(default_factory=lambda: ["SELECT"])

    # Forbidden functions
    forbidden_functions: list[str] = field(default_factory=lambda: [
        "pg_read_file",
        "pg_read_binary_file",
        "pg_ls_dir",
        "pg_stat_file",
        "system",
        "eval",
        "exec",
        "query_to_xml",
        "current_setting",
        "set_config",
        "pg_sleep",
        "lo_import",
        "lo_export",
        "dblink",
    ])


security_config = SecurityConfig()

# Inno Markaz — Project Specification & Master Architecture ("ABOUT.md")

## 1. Project Overview & Purpose

**Inno Markaz** is an enterprise AI agent system that provides a secure, natural-language interface to a PostgreSQL database. It enables users operating under a unified **`viewer` (read-only)** role to query workforce analytics, organizational structure, employee distribution, individual salaries, and contact details in Uzbek, Russian, or English.

### Foundational Principles:
1. **Unrestricted Business Read Access:** The user can query and view any business entity, including individual salaries, personal phone numbers, emails, and educational records.
2. **Strict Zero-Write Policy:** The database is completely protected against modifications. Users cannot insert, update, delete, truncate, drop, alter, or create any database records or schemas.
3. **Session Conversation Memory:** Retains the last 10 messages (user inquiries and assistant responses) per session for seamless multi-turn conversations.
4. **Beautiful Markdown Formatting:** Analytical responses are structured using polished Markdown (bold highlights, summary tables, and clear lists).
5. **Prompt Injection & Tag Defense:** Untrusted input is never wrapped in pseudo-XML tags (`<USER>`, `<USER_QUESTION>`). Direct prompt injections, jailbreaks (`DAN mode`), and stacked SQL commands are actively intercepted and blocked.
6. **PostgreSQL Read-Only User:** The application connects using a dedicated `inno_readonly` database user and executes within explicit `readonly=True` transactions.
7. **Per-Stage Timing Visibility:** Every stage of the MCP pipeline records and displays its exact execution time in seconds (e.g. `0.25 s`, `1.20 s`).
8. **Person Search with Exact & Fuzzy Fallback:** Queries for specific people (`employee_details`) display full profiles on exact match, or retrieve similarly named employees via `ILIKE` on partial/unmatched names.
9. **Maximum Token Limit (5000 tokens):** Supported generation budget of up to 5000 tokens for comprehensive analytics.
10. **Polished Table Styling:** Markdown tables render with clean borders, padded cells, alternating row backgrounds, and horizontal scroll support.

---

## 2. Technical Stack & Versions

- **Python Runtime:** `3.12.x` (strictly `>=3.12,<3.13`, verified with `3.12.7` / `3.12.10`).
- **HTTP / Web Framework:** `FastAPI` (>=0.115.0), ASGI server `uvicorn` (>=0.32.0).
- **Configuration & Validation:** `Pydantic` v2 (>=2.9.0) and `pydantic-settings` (>=2.6.0).
- **Database Engine & Driver:** PostgreSQL (>=14), connected via asynchronous driver `asyncpg` (>=0.30.0) with connection pooling and `readonly=True` transactions.
- **SQL Parsing & AST Security:** `sqlglot` (>=25.26.0) targeting PostgreSQL dialect.
- **LLM Integration:** `httpx` (>=0.27.0) integrating Ollama (local) and OpenRouter (cloud) behind an abstract `LLMProvider` interface.
- **Conversation Memory:** In-memory sliding window manager (`ConversationMemoryManager`, max 10 messages).
- **Frontend Layer:** Static single-page application (HTML5, modern CSS3, vanilla JavaScript, marked.js) served directly by FastAPI.
- **Testing Suite:** `pytest` (>=8.3.0) and `pytest-asyncio` (>=0.24.0).

---

## 3. Core Architecture & Request Lifecycle

```text
Browser / Static Frontend (Session ID: sess_...)
        │
        │ POST /api/chat { message, user_role: "viewer", session_id }
        ▼
   FastAPI Route
        │
        ▼
[MCP] 1. Input Validation (Checks prompt injection, tag injection, length, DDL/DML rejection)  [~0.01 s]
        │
        ▼
[MCP] 2. Schema Resolution & Memory Lookup (Loads schema context and retrieves last 10 messages) [~0.01 s]
        │
        ▼
[LLM] 3. Query Planner (Analyzes intent and entities with conversational context)              [~0.80 s]
        │
        ▼
[MCP] 4. Schema Mapping (Resolves Uzbek/Russian tokens to database columns and enums)          [~0.01 s]
        │
        ▼
[MCP] 5. Authorization Check (Verifies viewer read-only role, blocks write intents)            [~0.00 s]
        │
        ▼
[MCP] 6. SQL Generation (Produces deterministic parameterized SQL query)                       [~0.00 s]
        │
        ▼
[MCP] 7. SQL AST Validation (sqlglot: single SELECT only, table allowlist, reject SELECT *)    [~0.02 s]
        │
        ▼
[MCP] 8. Sensitivity Policy (Approves business read access, blocks catalog snooping)           [~0.00 s]
        │
        ▼
[MCP] 9. Complexity Check (Join count, column limit, and pagination compliance)                [~0.00 s]
        │
        ▼
[MCP] 10. Parameterization (Binds $1, $2 typed parameters, normalizes date objects)            [~0.00 s]
        │
        ▼
[POSTGRESQL] 11. Database Execution (Read-only user & transaction, statement_timeout)         [~0.05 s]
        │
        ▼
[MCP] 12. Result Sanitizer (Normalizes types, preserves business data including salaries)     [~0.00 s]
        │
        ▼
[LLM] 13. Answer Synthesizer (Generates grounded, beautiful Markdown tables and text)          [~1.20 s]
        │
        ▼
   Session Memory Update (Appends user message & assistant answer to sliding window)
        │
        ▼
   FastAPI Response ──► Client
```

---

## 4. API Endpoints

### `POST /api/chat`
- **Request Body:**
  ```json
  {
    "message": "Ali Valiyevning maoshi va telefoni qancha?",
    "user_role": "viewer",
    "session_id": "sess_1727771234_abc12"
  }
  ```
- **Response Body:**
  ```json
  {
    "success": true,
    "answer": "Ali Valiyev bo'yicha ma'lumotlar:\n\n| Maydon | Qiymat |\n|:---|:---|\n| **Lavozim** | Senior Backend Developer |\n| **Maosh** | 50,000,000.00 so'm |\n| **Telefon** | +998901234567 |",
    "sql": "SELECT e.first_name, e.last_name, p.name AS position, e.salary, e.phone FROM employees e JOIN positions p ON p.position_id = e.position_id WHERE e.first_name ILIKE $1 AND e.last_name ILIKE $2 LIMIT $3",
    "query_plan": { "intent": "employee_list", "entities": { ... } },
    "results": [ ... ],
    "row_count": 1,
    "execution_time_ms": 1450.2,
    "request_id": "uuid-v4",
    "session_id": "sess_1727771234_abc12",
    "stages": [
      { "stage": "INPUT_VALIDATION", "status": "passed", "detail": "...", "duration": "0.01 s" },
      { "stage": "POSTGRESQL", "status": "executed", "detail": "...", "duration": "0.05 s" },
      { "stage": "LLM_ANSWER", "status": "synthesized", "detail": "...", "duration": "1.20 s" }
    ]
  }
  ```

---

## 5. Security & Prompt Injection Defenses

1. **Anti-Tag Injection:** Rejects inputs with `<USER>`, `<SYSTEM>`, `<PROMPT>` tags.
2. **Anti-Jailbreak Filter:** Detects and terminates prompts containing `Ignore previous instructions`, `DAN mode`, `act as unrestricted`, `reveal system prompt`.
3. **Anti-Stacked SQL:** Blocks `; --`, `; DROP`, `; DELETE` patterns.
4. **AST Single-Statement Select:** sqlglot guarantees that only 1 statement exists and that it is an AST `exp.Select`.
5. **Database-Level Read-Only Guarantee:** The PostgreSQL user is `inno_readonly` and transactions are `readonly=True`. Even if an injection bypassed software filters, the PostgreSQL engine itself will reject any write.

# Inno Markaz — Project Specification & Master Architecture ("ABOUT.md")

## 1. Project Overview & Purpose

**Inno Markaz** is a production-grade enterprise AI agent system that provides a secure, natural-language interface to a PostgreSQL database. It enables internal organizational users (viewers, analysts, HR administrators, and superadmins) to query workforce analytics, organizational structure, employee distribution, and aggregated salary metrics in Uzbek, Russian, or English.

The foundational design principle is **strict isolation between the LLM and the database**. The LLM never possesses direct database access. Instead, all natural language interactions are converted into structured query plans and passed through a deterministic **Model Context Protocol (MCP)** security and execution pipeline.

---

## 2. Technical Stack & Versions

- **Python Runtime:** `3.12.x` (strictly `>=3.12,<3.13`, verified with `3.12.7` / `3.12.10`).
- **HTTP / Web Framework:** `FastAPI` (>=0.115.0), ASGI server `uvicorn` (>=0.32.0).
- **Configuration & Validation:** `Pydantic` v2 (>=2.9.0) and `pydantic-settings` (>=2.6.0).
- **Database Engine & Driver:** PostgreSQL (>=14), connected via asynchronous driver `asyncpg` (>=0.30.0).
- **SQL Parsing & AST Security:** `sqlglot` (>=25.26.0) targeting PostgreSQL dialect.
- **LLM Integration:** `httpx` (>=0.27.0) integrating Ollama (local) and OpenRouter (cloud) behind an abstract `LLMProvider` interface.
- **Frontend Layer:** Static single-page application (HTML5, modern CSS3, vanilla JavaScript) served directly by FastAPI.
- **Testing Suite:** `pytest` (>=8.3.0) and `pytest-asyncio` (>=0.24.0).

---

## 3. Core Architecture & Request Lifecycle

```text
Browser / Static Frontend
        │
        │ POST /api/chat
        ▼
   FastAPI Route
        │
        ▼
[MCP] 1. Input Validation (Length limits, null-byte checks, destructive SQL rejection)
        │
        ▼
[LLM] 2. Query Planner (Extracts intent, entities, dimensions, metrics, filters)
        │
        ▼
[MCP] 3. Schema Resolution (Resolves NL terms to exact schema tables, columns, enums)
        │
        ▼
[MCP] 4. Authorization Check (Role permissions: viewer, analyst, hr_admin, superadmin)
        │
        ▼
[MCP] 5. SQL Generation (Deterministic, parameterized PostgreSQL query generation)
        │
        ▼
[MCP] 6. SQL AST Validation (sqlglot AST inspection: single SELECT only, table allowlist, reject SELECT *)
        │
        ▼
[MCP] 7. Sensitivity Policy (Blocks individual salary disclosure and personal contact exposure)
        │
        ▼
[MCP] 8. Complexity Check (Join count, column limit, and pagination compliance)
        │
        ▼
[MCP] 9. Parameterization ($1, $2 typed parameters binding, date object normalization)
        │
        ▼
[POSTGRESQL] 10. Database Execution (Read-only transaction, statement_timeout enforcement)
        │
        ▼
[MCP] 11. Result Sanitizer (Masks/strips any residual sensitive fields)
        │
        ▼
[LLM] 12. Answer Synthesizer (Produces grounded natural language Uzbek response)
        │
        ▼
   FastAPI Response ──► Client
```

---

## 4. Database Schema Specification

The database models a corporate hierarchy across 6 core tables:

### 4.1 `departments`
- `department_id` (`integer`, PK): Primary identifier.
- `name` (`varchar(100)`, UNIQUE, NOT NULL): Department name.
- `description` (`text`): Department description.
- `manager_employee_id` (`char(6)`): Manager reference (soft reference, not a formal FK).
- `is_active` (`boolean`, NOT NULL, DEFAULT TRUE): Active flag.

### 4.2 `specialties`
- `specialty_id` (`integer`, PK): Primary identifier.
- `name` (`varchar(100)`, UNIQUE, NOT NULL): Specialty name.
- `description` (`text`): Description.
- `department_id` (`integer`, NOT NULL, FK -> `departments.department_id`).

### 4.3 `positions`
- `position_id` (`integer`, PK): Primary identifier.
- `name` (`varchar(100)`, NOT NULL): Position title.
- `level` (`varchar(20)`, NOT NULL, CHECK: `'Junior'`, `'Middle'`, `'Senior'`, `'Lead'`, `'Manager'`, `'Head'`).
- `department_id` (`integer`, NOT NULL, FK -> `departments.department_id`).
- `description` (`text`): Description.
- Constraint: `UNIQUE (department_id, name)`.

### 4.4 `employees`
- `employee_id` (`char(6)`, PK, CHECK: `~ '^[a-z]{6}$'`): 6-letter lowercase ID.
- `first_name` (`varchar(50)`, NOT NULL), `last_name` (`varchar(50)`, NOT NULL), `middle_name` (`varchar(50)`).
- `email` (`varchar(120)`, NOT NULL, UNIQUE), `phone` (`varchar(20)`, NOT NULL).
- `department_id` (`integer`, NOT NULL, FK -> `departments.department_id`).
- `specialty_id` (`integer`, NOT NULL, FK -> `specialties.specialty_id`).
- `position_id` (`integer`, NOT NULL, FK -> `positions.position_id`).
- `hire_date` (`date`, NOT NULL).
- `employment_type` (`varchar(20)`, NOT NULL, CHECK: `'Full-time'`, `'Part-time'`, `'Contract'`, `'Intern'`).
- `employment_status` (`varchar(20)`, NOT NULL, CHECK: `'Active'`, `'On Leave'`, `'Probation'`, `'Resigned'`).
- `work_format` (`varchar(20)`, NOT NULL, CHECK: `'Office'`, `'Remote'`, `'Hybrid'`).
- `office_location` (`varchar(100)`).
- `salary` (`numeric(12,2)`, NOT NULL, CHECK: `> 0`): Highly sensitive.
- `experience_years` (`numeric(4,1)`, NOT NULL, CHECK: `>= 0`).
- `manager_employee_id` (`char(6)`, FK -> `employees.employee_id`): Self-referencing FK.
- `is_active` (`boolean`, NOT NULL, DEFAULT TRUE).
- Constraints: `chk_not_own_manager`, `chk_resigned_inactive`.

### 4.5 `employee_contacts`
- `contact_id` (`integer`, PK generated by default).
- `employee_id` (`char(6)`, NOT NULL, FK -> `employees.employee_id` ON DELETE CASCADE).
- `contact_type` (`varchar(30)`, NOT NULL, CHECK: `'phone'`, `'telegram'`, `'personal_email'`).
- `contact_value` (`varchar(150)`, NOT NULL): Highly sensitive personal info.
- `is_primary` (`boolean`, NOT NULL, DEFAULT FALSE).

### 4.6 `employee_education`
- `education_id` (`integer`, PK generated by default).
- `employee_id` (`char(6)`, NOT NULL, FK -> `employees.employee_id` ON DELETE CASCADE).
- `institution` (`varchar(200)`, NOT NULL), `degree` (`varchar(50)`, NOT NULL).
- `field_of_study` (`varchar(100)`), `start_year` (`integer`), `end_year` (`integer`).
- `education_type` (`varchar(30)`, CHECK: `'Full-time'`, `'Part-time'`, `'Online'`, `'Bootcamp'`).

---

## 5. Security & Business Policies

1. **Read-Only Invariant:** Any statement other than a single `SELECT` query triggers immediate termination and an AST violation response.
2. **Strict Select Star Rejection:** Queries containing `SELECT *` are blocked by the AST validator (unless wrapped within aggregate `COUNT(*)`).
3. **Salary Policy:**
   - Aggregated salary metrics (`AVG(salary)`, `MIN(salary)`, `MAX(salary)`) grouped by department or level are permitted for analysts and admins.
   - Exact individual salary disclosure (`SELECT salary FROM employees WHERE employee_id = ...`) is prohibited unless explicitly authorized.
4. **Personal Contact Information:**
   - Raw contact values (`contact_value`, `phone`, `personal_email`, `telegram`) are classified as protected personal data and denied to default roles.
5. **Database Execution Constraints:**
   - All executions are wrapped in `async with conn.transaction(readonly=True)`.
   - `SET LOCAL statement_timeout` is set to `5000ms`.

---

## 6. API Endpoints

### `POST /api/chat`
- **Request Body:**
  ```json
  {
    "message": "Toshkentdagi faol xodimlar soni nechta?",
    "user_role": "analyst"
  }
  ```
- **Response Body:**
  ```json
  {
    "success": true,
    "answer": "Toshkent shahrida faol ishlayotgan xodimlar soni jami 24 nafar.",
    "sql": "SELECT COUNT(*) AS employee_count FROM employees e WHERE e.office_location ILIKE $1 AND e.is_active = $2",
    "query_plan": { "intent": "employee_count", "entities": { ... } },
    "results": [{ "employee_count": 24 }],
    "row_count": 1,
    "execution_time_ms": 142.5,
    "request_id": "uuid-v4",
    "stages": [ { "stage": "INPUT_VALIDATION", "status": "passed", "detail": "..." } ]
  }
  ```

### `GET /api/health`
- Verifies database pool connectivity and LLM endpoint availability.
- Returns status (`healthy` or `degraded`).

### `GET /api/config`
- Returns sanitized runtime metadata: application name, active LLM provider, active model, and environment.

### `GET /api/schema`
- Returns public schema metadata and column names for client-side table explorer.

---

## 7. Environment Variables Reference

| Variable | Description | Example / Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@localhost:5432/inno_markaz` |
| `LLM_PROVIDER` | Active LLM backend (`openrouter` or `ollama`) | `openrouter` |
| `OLLAMA_BASE_URL` | Ollama HTTP endpoint | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama model tag | `gemma4:latest` |
| `OPENROUTER_API_KEY` | OpenRouter API authentication key | `sk-or-v1-...` |
| `OPENROUTER_BASE_URL`| OpenRouter API endpoint | `https://openrouter.ai/api/v1` |
| `OPENROUTER_MODEL` | OpenRouter model string | `anthropic/claude-3.5-sonnet` |
| `APP_ENV` | Application environment | `development` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `HOST` | FastAPI bind host | `127.0.0.1` |
| `PORT` | FastAPI bind port | `8000` |

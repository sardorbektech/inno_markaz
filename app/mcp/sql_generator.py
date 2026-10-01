"""Deterministic and Safe SQL Generator from Structured Query Plans.

Implements query patterns described in AGENTS.md Sections 17-23, 55-58.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from app.db.schema import ALLOWED_POSITION_LEVELS, ALLOWED_WORK_FORMATS
from app.logging_config import log_stage


class SQLGenerator:
    """Generates standard parameterized SQL queries directly from structured query plans."""

    def generate_from_plan(
        self,
        plan: dict[str, Any],
        request_id: str | None = None,
    ) -> tuple[str, list[Any]]:
        """Generates standard read-only parameterized PostgreSQL query from a structured query plan.

        Returns:
            (sql_query_with_placeholders, parameter_values)
        """
        intent = plan.get("intent", "employee_count")
        entities = plan.get("entities", {}) or {}
        metrics = plan.get("metrics", ["count"])
        filters = plan.get("filters", []) or []
        limit = plan.get("limit", 10)
        sort_directives = plan.get("sort", []) or []

        log_stage("SQL_GENERATION", f"Generating SQL from plan intent: {intent}", request_id=request_id)

        params: list[Any] = []

        def add_param(val: Any) -> str:
            params.append(val)
            return f"${len(params)}"

        # 0. Specific Employee Details / Person Search (with exact and fuzzy similar name matching)
        first_name = (entities.get("first_name") or "").strip()
        last_name = (entities.get("last_name") or "").strip()
        search_query = (entities.get("search_query") or "").strip()

        if not first_name and not last_name and search_query:
            tokens = search_query.split()
            if len(tokens) >= 2:
                first_name, last_name = tokens[0], tokens[1]
            elif len(tokens) == 1:
                first_name = tokens[0]

        if intent == "employee_details" or first_name or last_name:
            base_select = (
                "SELECT e.employee_id, e.first_name, e.last_name, "
                "p.name AS position, p.level, d.name AS department, "
                "s.name AS specialty, e.salary, e.experience_years, "
                "e.work_format, e.office_location, e.employment_status, "
                "e.employment_type, e.hire_date, e.email, e.phone "
                "FROM employees e "
                "JOIN positions p ON p.position_id = e.position_id "
                "JOIN departments d ON d.department_id = e.department_id "
                "LEFT JOIN specialties s ON s.specialty_id = e.specialty_id"
            )

            if first_name and last_name:
                p1 = add_param(f"%{first_name}%")
                p2 = add_param(f"%{last_name}%")
                sql = (
                    f"{base_select} "
                    f"WHERE (e.first_name ILIKE {p1} AND e.last_name ILIKE {p2}) "
                    f"   OR (e.first_name ILIKE {p2} AND e.last_name ILIKE {p1}) "
                    f"   OR e.first_name ILIKE {p1} "
                    f"   OR e.last_name ILIKE {p2} "
                    f"   OR e.first_name ILIKE {p2} "
                    f"   OR e.last_name ILIKE {p1} "
                    "ORDER BY "
                    f"   CASE "
                    f"     WHEN (e.first_name ILIKE {p1} AND e.last_name ILIKE {p2}) OR (e.first_name ILIKE {p2} AND e.last_name ILIKE {p1}) THEN 1 "
                    f"     WHEN e.first_name ILIKE {p1} OR e.last_name ILIKE {p2} THEN 2 "
                    f"     ELSE 3 "
                    f"   END, "
                    "   e.employee_id ASC "
                    f"LIMIT {add_param(limit or 10)}"
                )
                return sql, params
            elif first_name or last_name:
                target_name = first_name or last_name
                p1 = add_param(f"%{target_name}%")
                sql = (
                    f"{base_select} "
                    f"WHERE e.first_name ILIKE {p1} OR e.last_name ILIKE {p1} "
                    "ORDER BY "
                    f"   CASE WHEN e.first_name ILIKE {p1} THEN 1 ELSE 2 END, "
                    "   e.employee_id ASC "
                    f"LIMIT {add_param(limit or 10)}"
                )
                return sql, params

        # 1. Salary Analytics (Section 23, 56)
        if intent == "salary_analytics" or any("salary" in m for m in metrics):
            sql = (
                "SELECT d.name AS department, "
                "ROUND(AVG(e.salary)::numeric, 2) AS average_salary, "
                "ROUND(MIN(e.salary)::numeric, 2) AS min_salary, "
                "ROUND(MAX(e.salary)::numeric, 2) AS max_salary, "
                "COUNT(e.employee_id) AS employee_count "
                "FROM departments d "
                "JOIN employees e ON e.department_id = d.department_id "
                "GROUP BY d.department_id, d.name "
                "ORDER BY average_salary DESC"
            )
            return sql, params

        # 2. Manager Analytics (Section 22)
        if intent == "manager_analytics":
            sql = (
                "SELECT m.employee_id, m.first_name, m.last_name, "
                "COUNT(e.employee_id) AS direct_report_count "
                "FROM employees m "
                "JOIN employees e ON e.manager_employee_id = m.employee_id "
                "GROUP BY m.employee_id, m.first_name, m.last_name "
                "ORDER BY direct_report_count DESC"
            )
            if limit:
                sql += f" LIMIT {add_param(limit)}"
            return sql, params

        # 3. Department Analytics / Top departments (Section 17.3, 18, 58)
        if intent == "department_analytics" or ("department" in plan.get("dimensions", []) and "count" in metrics):
            sql = (
                "SELECT d.name AS department, COUNT(e.employee_id) AS employee_count "
                "FROM departments d "
                "LEFT JOIN employees e ON e.department_id = d.department_id "
                "GROUP BY d.department_id, d.name "
                "ORDER BY employee_count DESC"
            )
            if limit:
                sql += f" LIMIT {add_param(limit)}"
            return sql, params

        # 4. Specialty Analytics (Section 21)
        if intent == "specialty_analytics" or ("specialty" in plan.get("dimensions", []) and "count" in metrics):
            sql = (
                "SELECT s.name AS specialty, COUNT(e.employee_id) AS employee_count "
                "FROM specialties s "
                "LEFT JOIN employees e ON e.specialty_id = s.specialty_id "
                "GROUP BY s.specialty_id, s.name "
                "ORDER BY employee_count DESC"
            )
            if limit:
                sql += f" LIMIT {add_param(limit)}"
            return sql, params

        # 5. Top-N Experience Employees (Section 18, 57)
        if any(s.get("field") in ("experience_years", "tajriba") for s in sort_directives):
            sql = (
                "SELECT e.employee_id, e.first_name, e.last_name, "
                "p.name AS position, d.name AS department, e.experience_years "
                "FROM employees e "
                "JOIN positions p ON p.position_id = e.position_id "
                "JOIN departments d ON d.department_id = e.department_id "
                "ORDER BY e.experience_years DESC "
                f"LIMIT {add_param(limit or 10)}"
            )
            return sql, params

        # 6. Employee List / Department + Position list (Section 20, 55)
        if intent == "employee_list" or "list" in metrics:
            where_clauses: list[str] = []

            # Check for position level filter
            level = entities.get("position_level")
            if level and level in ALLOWED_POSITION_LEVELS:
                where_clauses.append(f"p.level = {add_param(level)}")

            # Check for work format
            format_val = entities.get("work_format")
            if format_val and format_val in ALLOWED_WORK_FORMATS:
                where_clauses.append(f"e.work_format = {add_param(format_val)}")

            # Check for location
            loc = entities.get("office_location")
            if loc:
                where_clauses.append(f"e.office_location ILIKE {add_param(f'%{loc}%')}")

            # Check for year / hire date
            year = entities.get("year")
            if year:
                where_clauses.append(f"e.hire_date >= {add_param(date(year, 1, 1))}")
                where_clauses.append(f"e.hire_date < {add_param(date(year + 1, 1, 1))}")

            # Check filters list
            for flt in filters:
                f_name = flt.get("field", "")
                op = flt.get("operator", "=")
                val = flt.get("value")
                if f_name == "is_active":
                    where_clauses.append(f"e.is_active = {add_param(val)}")
                elif f_name == "employment_status":
                    where_clauses.append(f"e.employment_status = {add_param(val)}")

            where_str = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

            sql = (
                "SELECT e.employee_id, e.first_name, e.last_name, "
                "p.name AS position, p.level, d.name AS department, "
                "e.hire_date, e.work_format, e.office_location "
                "FROM employees e "
                "JOIN positions p ON p.position_id = e.position_id "
                "JOIN departments d ON d.department_id = e.department_id"
                f"{where_str} "
                f"LIMIT {add_param(limit or 10)}"
            )
            return sql, params

        # 7. Employee Count (Default pattern, Section 17.1, 17.2)
        where_clauses = []
        needs_position_join = False
        needs_dept_join = False

        # Level filter
        level = entities.get("position_level")
        if level and level in ALLOWED_POSITION_LEVELS:
            needs_position_join = True
            where_clauses.append(f"p.level = {add_param(level)}")

        # Work format filter
        format_val = entities.get("work_format")
        if format_val and format_val in ALLOWED_WORK_FORMATS:
            where_clauses.append(f"e.work_format = {add_param(format_val)}")

        # Location filter
        loc = entities.get("office_location")
        if loc:
            where_clauses.append(f"e.office_location ILIKE {add_param(f'%{loc}%')}")

        # Year filter
        year = entities.get("year")
        if year:
            where_clauses.append(f"e.hire_date >= {add_param(date(year, 1, 1))}")
            where_clauses.append(f"e.hire_date < {add_param(date(year + 1, 1, 1))}")

        # Active / status filters
        for flt in filters:
            f_name = flt.get("field", "")
            val = flt.get("value")
            if f_name == "is_active":
                where_clauses.append(f"e.is_active = {add_param(val)}")
            elif f_name == "employment_status":
                where_clauses.append(f"e.employment_status = {add_param(val)}")

        joins_str = ""
        if needs_position_join:
            joins_str += " JOIN positions p ON p.position_id = e.position_id"
        if needs_dept_join:
            joins_str += " JOIN departments d ON d.department_id = e.department_id"

        where_str = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        sql = f"SELECT COUNT(*) AS employee_count FROM employees e{joins_str}{where_str}"
        return sql, params


sql_generator = SQLGenerator()

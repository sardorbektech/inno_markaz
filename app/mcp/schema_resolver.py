"""Schema Resolver according to AGENTS.md Sections 12-16, 43-44.

Maps natural-language Uzbek/Russian/English terms to exact database columns,
tables, enums, and validated entities.
"""

from __future__ import annotations

import re
from typing import Any
from app.db.schema import (
    ALLOWED_EMPLOYMENT_STATUSES,
    ALLOWED_EMPLOYMENT_TYPES,
    ALLOWED_POSITION_LEVELS,
    ALLOWED_WORK_FORMATS,
    ALLOWED_DEPARTMENTS,
    ALLOWED_SPECIALTIES,
)
from app.logging_config import log_stage

# Natural Language Mappings
TERM_MAPPINGS: dict[str, dict[str, str]] = {
    # Work formats
    "work_format": {
        "masofaviy": "Remote",
        "masofadan": "Remote",
        "remote": "Remote",
        "ondariq": "Remote",
        "uyda": "Remote",
        "uydan": "Remote",
        "gibrid": "Hybrid",
        "hybrid": "Hybrid",
        "ofis": "Office",
        "ofisda": "Office",
        "office": "Office",
    },
    # Position levels
    "position_level": {
        "junior": "Junior",
        "kichik": "Junior",
        "middle": "Middle",
        "orta": "Middle",
        "o'rta": "Middle",
        "senior": "Senior",
        "katta": "Senior",
        "lead": "Lead",
        "yetakchi": "Lead",
        "manager": "Manager",
        "menejer": "Manager",
        "head": "Head",
        "boshliq": "Head",
    },
    # Employment statuses
    "employment_status": {
        "faol": "Active",
        "ishlayotgan": "Active",
        "active": "Active",
        "mehnat tatili": "On Leave",
        "tatilda": "On Leave",
        "on leave": "On Leave",
        "sinov": "Probation",
        "sinov muddati": "Probation",
        "probation": "Probation",
        "ishdan bo'shagan": "Resigned",
        "boshagan": "Resigned",
        "bo'shagan": "Resigned",
        "resigned": "Resigned",
    },
    # Employment types
    "employment_type": {
        "to'liq": "Full-time",
        "toliq": "Full-time",
        "full-time": "Full-time",
        "fulltime": "Full-time",
        "yarim": "Part-time",
        "part-time": "Part-time",
        "parttime": "Part-time",
        "shartnoma": "Contract",
        "contract": "Contract",
        "stajor": "Intern",
        "intern": "Intern",
        "amaliyotchi": "Intern",
    },
}

DEPARTMENT_MAPPINGS: dict[str, str] = {
    "backend development": "Backend Development",
    "backend": "Backend Development",
    "frontend development": "Frontend Development",
    "frontend": "Frontend Development",
    "mobile development": "Mobile Development",
    "mobil": "Mobile Development",
    "mobile": "Mobile Development",
    "data engineering": "Data Engineering",
    "artificial intelligence & ml": "Artificial Intelligence & ML",
    "artificial intelligence": "Artificial Intelligence & ML",
    "ai & ml": "Artificial Intelligence & ML",
    "ai": "Artificial Intelligence & ML",
    "ml": "Artificial Intelligence & ML",
    "sun'iy intellekt": "Artificial Intelligence & ML",
    "cybersecurity": "Cybersecurity",
    "kiberxavfsizlik": "Cybersecurity",
    "devops & cloud": "DevOps & Cloud",
    "devops": "DevOps & Cloud",
    "cloud": "DevOps & Cloud",
    "quality assurance": "Quality Assurance",
    "qa": "Quality Assurance",
    "testlash": "Quality Assurance",
    "ui/ux design": "UI/UX Design",
    "ui/ux": "UI/UX Design",
    "ui": "UI/UX Design",
    "ux": "UI/UX Design",
    "dizayn": "UI/UX Design",
    "it support & service desk": "IT Support & Service Desk",
    "it support": "IT Support & Service Desk",
    "service desk": "IT Support & Service Desk",
    "product & project management": "Product & Project Management",
    "product management": "Product & Project Management",
    "project management": "Product & Project Management",
    "loyiha": "Product & Project Management",
    "mahsulot": "Product & Project Management",
}

SPECIALTY_MAPPINGS: dict[str, str] = {
    "backend engineering": "Backend Engineering",
    "frontend engineering": "Frontend Engineering",
    "mobile engineering": "Mobile Engineering",
    "data analytics": "Data Analytics",
    "machine learning": "Machine Learning",
    "information security": "Information Security",
    "cloud engineering": "Cloud Engineering",
    "software testing": "Software Testing",
    "business analysis": "Business Analysis",
}


class SchemaResolver:
    """Resolves natural language tokens and query plans to exact schema representations."""

    def resolve_plan(self, question: str, plan: dict[str, Any], request_id: str | None = None) -> dict[str, Any]:
        """Validates and enriches query plan entities, filters, and fields against schema semantics."""
        log_stage("SCHEMA_RESOLUTION", "Resolving plan entities against schema semantics...", request_id=request_id)
        q_lower = question.lower()
        resolved_plan = dict(plan)
        entities = dict(resolved_plan.get("entities", {}) or {})
        filters = list(resolved_plan.get("filters", []) or [])
        sort_directives = list(resolved_plan.get("sort", []) or [])

        # 0. Intent Refinement & Safe Defaults
        current_intent = resolved_plan.get("intent") or "unknown"

        # Check if question asks about managers and their direct reports
        is_manager_query = bool(re.search(r"\b(rahbar|rahbarga|rahbarlar|rahbarda|menejer|manager)\b", q_lower))
        if is_manager_query and any(w in q_lower for w in ("nechta", "soni", "biriktirilgan", "qo'l ostida", "bo'ysunuvchi", "har bir")):
            resolved_plan["intent"] = "manager_analytics"
        elif current_intent in ("unknown", ""):
            if is_manager_query:
                resolved_plan["intent"] = "manager_analytics"
            elif "mutaxassislik" in q_lower:
                resolved_plan["intent"] = "specialty_analytics"
            elif "maosh" in q_lower or "oylik" in q_lower or "salary" in q_lower:
                resolved_plan["intent"] = "salary_analytics"
            elif "har bir bo'lim" in q_lower or "bo'limda nechta" in q_lower or "bo'limlar" in q_lower:
                resolved_plan["intent"] = "department_analytics"
            elif any(w in q_lower for w in ("nechta", "soni", "jami")):
                resolved_plan["intent"] = "employee_count"
            else:
                resolved_plan["intent"] = "employee_list"

        # Check if question explicitly targets an individual person (e.g. "Rustam Ganiyev ma'lumotlarini bering", "Temur Abdullayev kim?")
        person_name_match = re.search(
            r"\b([A-Z][a-z']+)(?:\s+([A-Z][a-z']+))?\s+(?:kim\b|haqida|ma'lumotlarini|malumotlarini|profili)",
            question,
        )
        if person_name_match:
            first_w = person_name_match.group(1)
            second_w = person_name_match.group(2)
            if first_w not in ALLOWED_POSITION_LEVELS and first_w not in ALLOWED_DEPARTMENTS:
                resolved_plan["intent"] = "employee_details"
                entities["first_name"] = first_w
                if second_w and second_w not in ALLOWED_POSITION_LEVELS:
                    entities["last_name"] = second_w

        # If individual person details search was planned
        if resolved_plan.get("intent") == "employee_details":
            search_q = entities.get("search_query")
            if not entities.get("first_name") and search_q:
                tokens = search_q.strip().split()
                if len(tokens) >= 2:
                    entities["first_name"] = tokens[0]
                    entities["last_name"] = tokens[1]
                elif len(tokens) == 1:
                    entities["first_name"] = tokens[0]

        # 1. Resolve Position Level
        for term, level_val in TERM_MAPPINGS["position_level"].items():
            if re.search(rf"\b{term}\b", q_lower):
                entities["position_level"] = level_val
                if not any(f.get("field") in ("level", "positions.level") for f in filters):
                    filters.append({"field": "level", "operator": "=", "value": level_val})
                break

        # 2. Resolve Department (strictly word boundaries to avoid matching substrings like 'ml' inside 'hodimlar')
        for term, dept_val in DEPARTMENT_MAPPINGS.items():
            if re.search(rf"\b{re.escape(term)}\b", q_lower):
                entities["department"] = dept_val
                if not any(f.get("field") in ("department", "departments.name", "name") for f in filters):
                    filters.append({"field": "department", "operator": "=", "value": dept_val})
                break

        # 3. Resolve Specialty (strictly word boundaries)
        for term, spec_val in SPECIALTY_MAPPINGS.items():
            if re.search(rf"\b{re.escape(term)}\b", q_lower):
                entities["specialty"] = spec_val
                if not any(f.get("field") in ("specialty", "specialties.name") for f in filters):
                    filters.append({"field": "specialty", "operator": "=", "value": spec_val})
                break

        # 4. Resolve Work Format
        for term, format_val in TERM_MAPPINGS["work_format"].items():
            if re.search(rf"\b{term}\b", q_lower):
                entities["work_format"] = format_val
                if not any(f.get("field") == "work_format" for f in filters):
                    filters.append({"field": "work_format", "operator": "=", "value": format_val})
                break

        # 5. Resolve Employment Status
        for term, status_val in TERM_MAPPINGS["employment_status"].items():
            if re.search(rf"\b{term}\b", q_lower):
                entities["employment_status"] = status_val
                if not any(f.get("field") == "employment_status" for f in filters):
                    filters.append({"field": "employment_status", "operator": "=", "value": status_val})
                break

        # 6. Check Active Requirement
        is_asking_active = bool(re.search(r"\b(faol|hozir|hozirgi|ishlayotgan|active)\b", q_lower))
        if is_asking_active and not any(f.get("field") == "is_active" for f in filters):
            if entities.get("employment_status") != "Resigned":
                filters.append({"field": "is_active", "operator": "=", "value": True})

        # 7. Year Resolution
        year_match = re.search(r"\b(20[12]\d)\b", q_lower)
        if year_match:
            year_val = int(year_match.group(1))
            entities["year"] = year_val
            if any(term in q_lower for term in ("ishga kirgan", "qabul", "hired", "ishga olingan")):
                if not any("hire_date" in f.get("field", "") for f in filters):
                    filters.append({"field": "hire_date", "operator": ">=", "value": f"{year_val}-01-01"})
                    filters.append({"field": "hire_date", "operator": "<", "value": f"{year_val + 1}-01-01"})

        # 8. Location Resolution
        for loc in ["toshkent", "samarqand", "buxoro", "andijon", "farg'ona", "namangan"]:
            if loc in q_lower:
                entities["office_location"] = loc.capitalize()
                if not any(f.get("field") == "office_location" for f in filters):
                    filters.append({"field": "office_location", "operator": "ILIKE", "value": f"%{loc.capitalize()}%"})
                break

        # 9. Top N Limit Detection / All Rows
        limit_match = re.search(r"\b(\d+)\s*ta\b", q_lower)
        if limit_match:
            resolved_plan["limit"] = int(limit_match.group(1))
        elif any(w in q_lower for w in ("hamma", "barcha", "to'liq", "all")):
            resolved_plan["limit"] = 500

        # 10. Experience Sort Directive
        if ("tajriba" in q_lower or "tajribasi" in q_lower or "tajribaga ega" in q_lower) and resolved_plan.get("intent") == "employee_list":
            if not any(s.get("field") == "experience_years" for s in sort_directives):
                sort_directives.append({"field": "experience_years", "direction": "DESC"})

        # 11. Validate Enums against Authoritative Constants
        if entities.get("position_level") and entities["position_level"] not in ALLOWED_POSITION_LEVELS:
            entities["position_level"] = None
        if entities.get("work_format") and entities["work_format"] not in ALLOWED_WORK_FORMATS:
            entities["work_format"] = None
        if entities.get("employment_status") and entities["employment_status"] not in ALLOWED_EMPLOYMENT_STATUSES:
            entities["employment_status"] = None
        if entities.get("employment_type") and entities["employment_type"] not in ALLOWED_EMPLOYMENT_TYPES:
            entities["employment_type"] = None

        resolved_plan["entities"] = entities
        resolved_plan["filters"] = filters
        resolved_plan["sort"] = sort_directives

        log_stage("SCHEMA_RESOLUTION", f"Resolved plan: intent={resolved_plan.get('intent')}, entities={entities}", request_id=request_id)
        return resolved_plan


schema_resolver = SchemaResolver()

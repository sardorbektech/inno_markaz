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
        "manager": "Manager",
        "menejer": "Manager",
        "head": "Head",
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

        # 0. Intent refinement based on domain keywords & entities
        # Check for person inquiry words
        is_person_inquiry = bool(re.search(r"\b(kim|haqida|ma'lumot|ma'lumotlarini|malumot|malumotlarini|profili|oyligi|maoshi)\b", q_lower))

        # Extract non-stopword tokens as potential person names
        stopwords = {
            "kim", "u", "haqida", "ma'lumot", "ma'lumotlarini", "malumot", "malumotlarini",
            "bering", "ayt", "ayting", "toping", "ko'rsating", "korsating", "iltimos",
            "qancha", "nechta", "qaysi", "bor", "mavjud", "xodim", "inson", "odam", "ishchi",
            "xodimlar", "maosh", "oylik", "tajriba", "tajribasi", "bo'lim", "bolim", "bo'limlar",
            "daraja", "darajasi", "katta", "kichik", "orta", "o'rta", "bosh", "ofis",
            "faol", "tatilda", "resigned", "remote", "hybrid", "office", "junior", "middle", "senior",
            "lead", "manager", "head", "full", "time", "part", "intern", "contract", "jami",
            "o'rtacha", "ortacha", "eng", "ko'p", "kop", "kam", "soni", "hisoboti"
        }
        tokens = [w for w in re.split(r"[^\w']+", question) if w]
        candidate_names = [w for w in tokens if w.lower() not in stopwords and not w.isdigit()]

        if resolved_plan.get("intent") == "employee_details" or entities.get("first_name") or entities.get("last_name") or entities.get("search_query"):
            resolved_plan["intent"] = "employee_details"
            if not entities.get("first_name") and candidate_names:
                entities["first_name"] = candidate_names[0]
                if len(candidate_names) >= 2:
                    entities["last_name"] = candidate_names[1]

        elif is_person_inquiry and candidate_names:
            resolved_plan["intent"] = "employee_details"
            entities["first_name"] = candidate_names[0]
            if len(candidate_names) >= 2:
                entities["last_name"] = candidate_names[1]

        elif len(candidate_names) == 2 and not any(kw in q_lower for kw in ("nechta", "qancha", "har bir", "jami")):
            resolved_plan["intent"] = "employee_details"
            entities["first_name"] = candidate_names[0]
            entities["last_name"] = candidate_names[1]

        elif "rahbar" in q_lower or "rahbarga" in q_lower:
            resolved_plan["intent"] = "manager_analytics"
        elif "mutaxassislik" in q_lower:
            resolved_plan["intent"] = "specialty_analytics"
        elif "maosh" in q_lower or "oylik" in q_lower or "salary" in q_lower:
            resolved_plan["intent"] = "salary_analytics"
        elif "har bir bo'lim" in q_lower or "bo'limda nechta" in q_lower or "bo'limlar" in q_lower:
            resolved_plan["intent"] = "department_analytics"
        elif "tajriba" in q_lower or "tajribasi" in q_lower or "tajribaga ega" in q_lower:
            resolved_plan["intent"] = "employee_list"
            if not any(s.get("field") == "experience_years" for s in sort_directives):
                sort_directives.append({"field": "experience_years", "direction": "DESC"})

        # Top N limit detection
        limit_match = re.search(r"\b(\d+)\s*ta\b", q_lower)
        if limit_match:
            resolved_plan["limit"] = int(limit_match.group(1))

        # 1. Resolve Work Format
        for term, format_val in TERM_MAPPINGS["work_format"].items():
            if re.search(rf"\b{term}\b", q_lower):
                entities["work_format"] = format_val
                if not any(f.get("field") == "work_format" for f in filters):
                    filters.append({"field": "work_format", "operator": "=", "value": format_val})
                break

        # 2. Resolve Position Level
        for term, level_val in TERM_MAPPINGS["position_level"].items():
            if re.search(rf"\b{term}\b", q_lower):
                entities["position_level"] = level_val
                if not any(f.get("field") in ("level", "positions.level") for f in filters):
                    filters.append({"field": "level", "operator": "=", "value": level_val})
                break

        # 3. Resolve Employment Status
        for term, status_val in TERM_MAPPINGS["employment_status"].items():
            if re.search(rf"\b{term}\b", q_lower):
                entities["employment_status"] = status_val
                if not any(f.get("field") == "employment_status" for f in filters):
                    filters.append({"field": "employment_status", "operator": "=", "value": status_val})
                break

        # 4. Check active requirement (Section 12)
        is_asking_active = bool(re.search(r"\b(faol|hozir|hozirgi|ishlayotgan|active)\b", q_lower))
        if is_asking_active and not any(f.get("field") == "is_active" for f in filters):
            if entities.get("employment_status") != "Resigned":
                filters.append({"field": "is_active", "operator": "=", "value": True})

        # 5. Year Resolution (Section 19: Date Questions)
        year_match = re.search(r"\b(20[12]\d)\b", q_lower)
        if year_match:
            year_val = int(year_match.group(1))
            entities["year"] = year_val
            if any(term in q_lower for term in ("ishga kirgan", "qabul", "hired", "ishga olingan")):
                if not any("hire_date" in f.get("field", "") for f in filters):
                    filters.append({"field": "hire_date", "operator": ">=", "value": f"{year_val}-01-01"})
                    filters.append({"field": "hire_date", "operator": "<", "value": f"{year_val + 1}-01-01"})

        # 6. Location Resolution
        for loc in ["toshkent", "samarqand", "buxoro", "andijon", "farg'ona", "namangan"]:
            if loc in q_lower:
                entities["office_location"] = loc.capitalize()
                if not any(f.get("field") == "office_location" for f in filters):
                    filters.append({"field": "office_location", "operator": "ILIKE", "value": f"%{loc.capitalize()}%"})
                break

        # 7. Validate enums
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

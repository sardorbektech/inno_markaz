"""Authoritative PostgreSQL Database Schema Definition and Metadata for Inno Markaz.

Conforms to AGENTS.md Sections 2-16, 26, 38.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SensitivityLevel = Literal["public", "internal", "personal", "sensitive"]


@dataclass(frozen=True)
class ColumnInfo:
    name: str
    data_type: str
    nullable: bool
    sensitivity: SensitivityLevel
    description: str


@dataclass(frozen=True)
class TableInfo:
    name: str
    primary_key: list[str]
    columns: dict[str, ColumnInfo]
    foreign_keys: dict[str, str]  # local_column -> referenced_table.referenced_column
    description: str


# Authoritative Allowed Enums / Checks
ALLOWED_POSITION_LEVELS: tuple[str, ...] = (
    "Junior",
    "Middle",
    "Senior",
    "Lead",
    "Manager",
    "Head",
)

ALLOWED_EMPLOYMENT_TYPES: tuple[str, ...] = (
    "Full-time",
    "Part-time",
    "Contract",
    "Intern",
)

ALLOWED_EMPLOYMENT_STATUSES: tuple[str, ...] = (
    "Active",
    "On Leave",
    "Probation",
    "Resigned",
)

ALLOWED_WORK_FORMATS: tuple[str, ...] = (
    "Office",
    "Remote",
    "Hybrid",
)

ALLOWED_CONTACT_TYPES: tuple[str, ...] = (
    "phone",
    "telegram",
    "personal_email",
)

ALLOWED_EDUCATION_TYPES: tuple[str, ...] = (
    "Full-time",
    "Part-time",
    "Online",
    "Bootcamp",
)

# Authoritative Allowed Tables (AGENTS.md Section 26)
ALLOWED_TABLES: tuple[str, ...] = (
    "departments",
    "specialties",
    "positions",
    "employees",
    "employee_contacts",
    "employee_education",
)

# Detailed Schema Definitions
SCHEMA_TABLES: dict[str, TableInfo] = {
    "departments": TableInfo(
        name="departments",
        primary_key=["department_id"],
        description="Company departments",
        foreign_keys={},  # Note: manager_employee_id is NOT a declared FK constraint in DB
        columns={
            "department_id": ColumnInfo("department_id", "integer", False, "internal", "Department identifier"),
            "name": ColumnInfo("name", "varchar(100)", False, "public", "Department name"),
            "description": ColumnInfo("description", "text", True, "internal", "Department description"),
            "manager_employee_id": ColumnInfo("manager_employee_id", "char(6)", True, "internal", "Manager employee ID"),
            "is_active": ColumnInfo("is_active", "boolean", False, "public", "Active flag"),
        },
    ),
    "specialties": TableInfo(
        name="specialties",
        primary_key=["specialty_id"],
        description="Professional specialties within departments",
        foreign_keys={"department_id": "departments.department_id"},
        columns={
            "specialty_id": ColumnInfo("specialty_id", "integer", False, "internal", "Specialty identifier"),
            "name": ColumnInfo("name", "varchar(100)", False, "public", "Specialty name"),
            "description": ColumnInfo("description", "text", True, "internal", "Specialty description"),
            "department_id": ColumnInfo("department_id", "integer", False, "internal", "Parent department ID"),
        },
    ),
    "positions": TableInfo(
        name="positions",
        primary_key=["position_id"],
        description="Job positions with seniority levels",
        foreign_keys={"department_id": "departments.department_id"},
        columns={
            "position_id": ColumnInfo("position_id", "integer", False, "internal", "Position identifier"),
            "name": ColumnInfo("name", "varchar(100)", False, "public", "Position name"),
            "level": ColumnInfo("level", "varchar(20)", False, "public", "Seniority level: Junior, Middle, Senior, Lead, Manager, Head"),
            "department_id": ColumnInfo("department_id", "integer", False, "internal", "Parent department ID"),
            "description": ColumnInfo("description", "text", True, "internal", "Position description"),
        },
    ),
    "employees": TableInfo(
        name="employees",
        primary_key=["employee_id"],
        description="Employee records and affiliations",
        foreign_keys={
            "department_id": "departments.department_id",
            "specialty_id": "specialties.specialty_id",
            "position_id": "positions.position_id",
            "manager_employee_id": "employees.employee_id",
        },
        columns={
            "employee_id": ColumnInfo("employee_id", "char(6)", False, "internal", "Unique 6-char employee ID"),
            "first_name": ColumnInfo("first_name", "varchar(50)", False, "personal", "First name"),
            "last_name": ColumnInfo("last_name", "varchar(50)", False, "personal", "Last name"),
            "middle_name": ColumnInfo("middle_name", "varchar(50)", True, "personal", "Middle name"),
            "email": ColumnInfo("email", "varchar(120)", False, "personal", "Work email"),
            "phone": ColumnInfo("phone", "varchar(20)", False, "personal", "Work phone"),
            "department_id": ColumnInfo("department_id", "integer", False, "internal", "Department ID"),
            "specialty_id": ColumnInfo("specialty_id", "integer", False, "internal", "Specialty ID"),
            "position_id": ColumnInfo("position_id", "integer", False, "internal", "Position ID"),
            "hire_date": ColumnInfo("hire_date", "date", False, "internal", "Employment start date"),
            "employment_type": ColumnInfo("employment_type", "varchar(20)", False, "internal", "Full-time, Part-time, Contract, Intern"),
            "employment_status": ColumnInfo("employment_status", "varchar(20)", False, "internal", "Active, On Leave, Probation, Resigned"),
            "work_format": ColumnInfo("work_format", "varchar(20)", False, "internal", "Office, Remote, Hybrid"),
            "office_location": ColumnInfo("office_location", "varchar(100)", True, "internal", "Office location"),
            "salary": ColumnInfo("salary", "numeric(12,2)", False, "sensitive", "Employee salary"),
            "experience_years": ColumnInfo("experience_years", "numeric(4,1)", False, "internal", "Years of experience"),
            "manager_employee_id": ColumnInfo("manager_employee_id", "char(6)", True, "internal", "Direct manager ID"),
            "is_active": ColumnInfo("is_active", "boolean", False, "internal", "Active employee flag"),
        },
    ),
    "employee_contacts": TableInfo(
        name="employee_contacts",
        primary_key=["contact_id"],
        description="Personal emergency and additional contacts",
        foreign_keys={"employee_id": "employees.employee_id"},
        columns={
            "contact_id": ColumnInfo("contact_id", "integer", False, "internal", "Contact ID"),
            "employee_id": ColumnInfo("employee_id", "char(6)", False, "internal", "Employee ID"),
            "contact_type": ColumnInfo("contact_type", "varchar(30)", False, "personal", "phone, telegram, personal_email"),
            "contact_value": ColumnInfo("contact_value", "varchar(150)", False, "personal", "Personal contact value"),
            "is_primary": ColumnInfo("is_primary", "boolean", False, "personal", "Primary contact flag"),
        },
    ),
    "employee_education": TableInfo(
        name="employee_education",
        primary_key=["education_id"],
        description="Education history of employees",
        foreign_keys={"employee_id": "employees.employee_id"},
        columns={
            "education_id": ColumnInfo("education_id", "integer", False, "internal", "Education ID"),
            "employee_id": ColumnInfo("employee_id", "char(6)", False, "internal", "Employee ID"),
            "institution": ColumnInfo("institution", "varchar(200)", False, "personal", "Educational institution"),
            "degree": ColumnInfo("degree", "varchar(50)", False, "personal", "Degree"),
            "field_of_study": ColumnInfo("field_of_study", "varchar(100)", True, "personal", "Field of study"),
            "start_year": ColumnInfo("start_year", "integer", True, "personal", "Start year"),
            "end_year": ColumnInfo("end_year", "integer", True, "personal", "End year"),
            "education_type": ColumnInfo("education_type", "varchar(30)", True, "personal", "Full-time, Part-time, Online, Bootcamp"),
        },
    ),
}


def is_allowed_table(table_name: str) -> bool:
    """Checks if a table is in the allowlist."""
    return table_name.lower().strip('"') in ALLOWED_TABLES


def is_allowed_column(table_name: str, column_name: str) -> bool:
    """Checks if a column belongs to an allowed table."""
    tbl = table_name.lower().strip('"')
    col = column_name.lower().strip('"')
    if tbl not in SCHEMA_TABLES:
        return False
    return col in SCHEMA_TABLES[tbl].columns


def is_sensitive_column(table_name: str, column_name: str) -> bool:
    """Checks if a column is sensitive or personal."""
    tbl = table_name.lower().strip('"')
    col = column_name.lower().strip('"')
    if tbl in SCHEMA_TABLES and col in SCHEMA_TABLES[tbl].columns:
        return SCHEMA_TABLES[tbl].columns[col].sensitivity in ("sensitive", "personal")
    return False


def get_compact_schema_context(include_sensitive: bool = False) -> dict[str, dict[str, object]]:
    """Returns a compact schema representation for the LLM prompt according to Section 38."""
    context: dict[str, dict[str, object]] = {}
    for tbl_name, tbl_info in SCHEMA_TABLES.items():
        cols: dict[str, str] = {}
        for col_name, col_info in tbl_info.columns.items():
            if not include_sensitive and col_info.sensitivity == "sensitive":
                # Only include salary if aggregate usage or explicitly authorized
                cols[col_name] = f"{col_info.data_type} (aggregate-only by default: AVG, MIN, MAX)"
            elif not include_sensitive and col_info.sensitivity == "personal":
                cols[col_name] = f"{col_info.data_type} (personal data, masked by default)"
            else:
                cols[col_name] = col_info.data_type

        context[tbl_name] = {
            "description": tbl_info.description,
            "columns": cols,
            "foreign_keys": tbl_info.foreign_keys,
        }
    return context

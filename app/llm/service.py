"""LLM Service Orchestration with grounded deterministic fallbacks."""

from __future__ import annotations

import json
import re
from typing import Any
from app.llm.factory import create_llm_provider
from app.llm.provider import LLMMessage, LLMProvider, LLMRequest
from app.logging_config import log_stage, logger
from app.prompts.answer_generator import (
    ANSWER_GENERATOR_SYSTEM_PROMPT,
    build_answer_prompt,
)
from app.prompts.query_planner import (
    QUERY_PLANNER_SYSTEM_PROMPT,
    build_query_planner_prompt,
)
from app.prompts.sql_generator import (
    SQL_GENERATOR_SYSTEM_PROMPT,
    build_sql_generator_prompt,
)


def extract_json_block(text: str) -> dict[str, Any]:
    """Extracts JSON object from markdown code fences or raw text."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        raw_json = match.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            raw_json = text[start : end + 1]
        else:
            raise ValueError(f"No JSON object found in response: {text[:200]}")

    return json.loads(raw_json)


def extract_sql_block(text: str) -> str:
    """Extracts SQL string from markdown fences or raw text."""
    text = text.strip()
    match = re.search(r"```(?:sql)?\s*(SELECT.*?;?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    select_match = re.search(r"\bSELECT\b[\s\S]+", text, re.IGNORECASE)
    if select_match:
        sql = select_match.group(0).strip()
        sql = re.sub(r"```.*$", "", sql, flags=re.DOTALL).strip()
        return sql
    return text


class LLMService:
    """Coordinates LLM generation stages."""

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider or create_llm_provider()

    async def plan_query(
        self,
        question: str,
        schema_context: dict[str, Any],
        history: list[dict[str, str]] | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Calls LLM to generate a structured query plan."""
        log_stage("LLM", f"Calling LLM for Query Planning on: {question}", request_id=request_id)
        prompt = build_query_planner_prompt(question, schema_context, history=history)

        req = LLMRequest(
            messages=[
                LLMMessage(role="system", content=QUERY_PLANNER_SYSTEM_PROMPT),
                LLMMessage(role="user", content=prompt),
            ],
            temperature=0.0,
            max_tokens=384,
        )

        try:
            resp = await self.provider.generate(req)
            plan = extract_json_block(resp.content)
            log_stage("QUERY_PLAN", f"Intent: {plan.get('intent')} | Metrics: {plan.get('metrics')}", request_id=request_id)
            return plan
        except Exception as e:
            logger.warning(f"Failed to parse JSON plan from LLM: {e}")
            return {
                "intent": "employee_count",
                "entities": {},
                "metrics": ["count"],
                "dimensions": [],
                "filters": [],
                "sort": [],
                "limit": 10,
            }

    async def generate_sql(
        self,
        question: str,
        query_plan: dict[str, Any],
        schema_context: dict[str, Any],
        request_id: str | None = None,
    ) -> str:
        """Calls LLM to produce candidate SQL query."""
        log_stage("SQL_GENERATION", "LLM generating candidate SQL query...", request_id=request_id)
        prompt = build_sql_generator_prompt(question, query_plan, schema_context)

        req = LLMRequest(
            messages=[
                LLMMessage(role="system", content=SQL_GENERATOR_SYSTEM_PROMPT),
                LLMMessage(role="user", content=prompt),
            ],
            temperature=0.0,
            max_tokens=384,
        )

        try:
            resp = await self.provider.generate(req)
            sql = extract_sql_block(resp.content)
            log_stage("SQL_GENERATION", f"Generated SQL candidate: {sql}", request_id=request_id)
            return sql
        except Exception as e:
            logger.warning(f"LLM SQL generation failed: {e}")
            return ""

    async def generate_answer(
        self,
        question: str,
        query_plan: dict[str, Any],
        sanitized_results: list[dict[str, Any]],
        row_count: int,
        history: list[dict[str, str]] | None = None,
        request_id: str | None = None,
    ) -> str:
        """Calls LLM to formulate natural language final answer based strictly on sanitized results."""
        log_stage("LLM_ANSWER", "Synthesizing grounded answer from sanitized results...", request_id=request_id)
        prompt = build_answer_prompt(question, query_plan, sanitized_results, row_count, history=history)

        req = LLMRequest(
            messages=[
                LLMMessage(role="system", content=ANSWER_GENERATOR_SYSTEM_PROMPT),
                LLMMessage(role="user", content=prompt),
            ],
            temperature=0.1,
            max_tokens=768,
        )

        answer = ""
        try:
            resp = await self.provider.generate(req)
            answer = resp.content.strip()
        except Exception as e:
            logger.warning(f"LLM answer generation failed: {e}")

        # Deterministic grounded fallback in beautiful Markdown if LLM produces empty response
        if not answer:
            if row_count == 0 or len(sanitized_results) == 0:
                answer = "Ma'lumotlar bazasida ushbu so'rov bo'yicha hech qanday ma'lumot topilmadi."
            elif row_count == 1 and "employee_count" in sanitized_results[0]:
                count_val = sanitized_results[0]["employee_count"]
                answer = f"So'rov natijasiga ko'ra, xodimlar soni jami **{count_val} nafar**."
            elif row_count == 1 and "total" in sanitized_results[0]:
                count_val = sanitized_results[0]["total"]
                answer = f"So'rov bo'yicha jami: **{count_val} nafar**."
            elif any("department" in r and "employee_count" in r for r in sanitized_results):
                table_rows = [f"| {r.get('department')} | **{r.get('employee_count')}** |" for r in sanitized_results[:15]]
                answer = (
                    "### Bo'limlar bo'yicha xodimlar soni\n\n"
                    "| Bo'lim | Xodimlar soni |\n"
                    "|:---|:---|\n" + "\n".join(table_rows)
                )
            elif any("average_salary" in r for r in sanitized_results):
                table_rows = [
                    f"| {r.get('department')} | {float(r.get('average_salary', 0)):,.2f} so'm | {float(r.get('min_salary', 0)):,.2f} so'm | {float(r.get('max_salary', 0)):,.2f} so'm |"
                    for r in sanitized_results[:15]
                ]
                answer = (
                    "### Bo'limlar bo'yicha o'rtacha maosh ko'rsatkichlari\n\n"
                    "| Bo'lim | O'rtacha maosh | Min maosh | Max maosh |\n"
                    "|:---|:---|:---|:---|\n" + "\n".join(table_rows)
                )
            elif any("specialty" in r and "employee_count" in r for r in sanitized_results):
                top_s = sanitized_results[0]
                table_rows = [f"| {r.get('specialty')} | **{r.get('employee_count')}** |" for r in sanitized_results[:15]]
                answer = (
                    f"Eng ko'p xodimga ega mutaxassislik: **{top_s.get('specialty')}** ({top_s.get('employee_count')} nafar).\n\n"
                    "| Mutaxassislik | Xodimlar soni |\n"
                    "|:---|:---|\n" + "\n".join(table_rows)
                )
            elif any("direct_report_count" in r for r in sanitized_results):
                table_rows = [f"| {r.get('first_name')} {r.get('last_name')} | **{r.get('direct_report_count')}** |" for r in sanitized_results[:15]]
                answer = (
                    "### Rahbarlar va ularga biriktirilgan xodimlar\n\n"
                    "| Rahbar | Biriktirilgan xodimlar |\n"
                    "|:---|:---|\n" + "\n".join(table_rows)
                )
            elif any("first_name" in r and "last_name" in r for r in sanitized_results):
                table_rows = [
                    f"| {r.get('first_name')} {r.get('last_name')} | {r.get('position', '-')} | {r.get('department', '-')} | {r.get('experience_years', '-')} |"
                    for r in sanitized_results[:15]
                ]
                answer = (
                    "### Xodimlar ro'yxati\n\n"
                    "| Ism, Familiya | Lavozim | Bo'lim | Tajriba (yil) |\n"
                    "|:---|:---|:---|:---|\n" + "\n".join(table_rows)
                )
            else:
                answer = f"So'rov muvaffaqiyatli bajarildi. Jami **{row_count} ta** yozuv topildi."

        log_stage("LLM_ANSWER", f"Answer generated ({len(answer)} chars)", request_id=request_id)
        return answer


llm_service = LLMService()

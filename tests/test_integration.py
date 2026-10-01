"""Integration Tests according to AGENTS.md Section 54 (Items 1-10)."""

import pytest
from app.mcp.executor import mcp_executor


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "question",
    [
        "Xodimlar soni nechta?",
        "Har bir bo'limda nechta xodim bor?",
        "Eng ko'p xodimga ega 10 ta bo'lim qaysilar?",
        "Senior xodimlar nechta?",
        "Remote xodimlar soni nechta?",
        "2026-yilda ishga kirgan xodimlar nechta?",
        "Har bir bo'limning o'rtacha maoshi qancha?",
        "Eng ko'p tajribaga ega 10 ta xodim kim?",
        "Har bir rahbarga nechta xodim biriktirilgan?",
        "Qaysi mutaxassislikda eng ko'p xodim bor?",
    ],
)
async def test_section_54_queries(question):
    """Executes the minimum test questions required by AGENTS.md Section 54."""
    result = await mcp_executor.process_question(raw_question=question, user_role="analyst")

    assert result.question == question
    assert result.sql.strip().upper().startswith("SELECT")
    assert result.row_count >= 0
    assert len(result.answer) > 0
    assert result.execution_time_ms > 0
    assert len(result.stages) > 0

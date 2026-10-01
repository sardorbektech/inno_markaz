"""Tests for Conversation Memory Manager (Last 10 Messages Window)."""

import pytest
from app.llm.memory import ConversationMemoryManager


def test_memory_sliding_window_10_messages():
    """Verifies that conversation memory stores exactly the last 10 messages."""
    memory = ConversationMemoryManager(max_messages=10)
    session_id = "test_session_1"

    # Add 12 messages
    for i in range(1, 13):
        role = "user" if i % 2 != 0 else "assistant"
        memory.add_message(session_id, role, f"Message {i}")

    history = memory.get_history(session_id)

    # Must contain exactly 10 messages
    assert len(history) == 10

    # Oldest message should be Message 3 (Message 1 and 2 evicted)
    assert history[0]["content"] == "Message 3"
    assert history[-1]["content"] == "Message 12"


def test_session_isolation():
    """Verifies that multiple sessions maintain isolated memories."""
    memory = ConversationMemoryManager(max_messages=10)

    memory.add_message("session_a", "user", "Question from A")
    memory.add_message("session_b", "user", "Question from B")

    history_a = memory.get_history("session_a")
    history_b = memory.get_history("session_b")

    assert len(history_a) == 1
    assert history_a[0]["content"] == "Question from A"

    assert len(history_b) == 1
    assert history_b[0]["content"] == "Question from B"


def test_format_history_without_xml_tags():
    """Verifies formatted history does not contain XML tags."""
    memory = ConversationMemoryManager(max_messages=10)
    session_id = "test_session_no_tags"

    memory.add_message(session_id, "user", "Who is the manager?")
    memory.add_message(session_id, "assistant", "Manager is Alice.")

    formatted = memory.format_history_for_prompt(session_id)

    assert "<USER>" not in formatted
    assert "<USER_QUESTION>" not in formatted
    assert "User: Who is the manager?" in formatted
    assert "Assistant: Manager is Alice." in formatted

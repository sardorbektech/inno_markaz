"""Session-based Conversation Memory Manager.

Retains the last 10 messages (user and assistant) per session for context-aware LLM planning and responses.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import time
from typing import Any


@dataclass
class ChatMessage:
    role: str  # "user" or "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)


class ConversationMemoryManager:
    """Manages short-term conversation memory with a sliding window of max 10 messages."""

    def __init__(self, max_messages: int = 10) -> None:
        self.max_messages = max_messages
        self._sessions: dict[str, deque[ChatMessage]] = {}

    def get_history(self, session_id: str) -> list[dict[str, str]]:
        """Returns the last messages for the given session."""
        if not session_id or session_id not in self._sessions:
            return []
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self._sessions[session_id]
        ]

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """Appends a new message to the session history, evicting oldest if exceeds max_messages."""
        if not session_id:
            return

        if session_id not in self._sessions:
            self._sessions[session_id] = deque(maxlen=self.max_messages)

        self._sessions[session_id].append(ChatMessage(role=role, content=content.strip()))

    def clear_session(self, session_id: str) -> None:
        """Clears memory for a specific session."""
        if session_id in self._sessions:
            del self._sessions[session_id]

    def format_history_for_prompt(self, session_id: str) -> str:
        """Formats the history as a clean, readable text block without XML tags."""
        history = self.get_history(session_id)
        if not history:
            return ""

        lines = ["### Recent Conversation History (Last 10 messages):"]
        for msg in history:
            prefix = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{prefix}: {msg['content']}")
        return "\n".join(lines)


conversation_memory = ConversationMemoryManager(max_messages=10)

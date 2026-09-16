"""Structured logging of WhatsApp conversations and tool calls, for the
dashboard (dashboard/) to read — separate from LangGraph's own checkpoint
tables (agent memory) that live in the *same* data/finbuddy.db file.
Checkpoint blobs are optimized for the agent to replay, not for a human or
a dashboard to query "show me today's decoded offers" — these two small
tables are the queryable, structured version of the same conversations.

Plain stdlib sqlite3, no ORM — two tables, simple enough not to need one.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "finbuddy.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tool_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    tool_input TEXT NOT NULL,
    tool_output TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def get_connection() -> sqlite3.Connection:
    """One connection per call — sqlite3 connections aren't safe to share
    across threads, and FastAPI may run request handlers on different
    threads. Cheap enough at this traffic volume; revisit with a pool if
    that changes. Ensures the schema exists every time (idempotent), so
    nothing else needs an explicit init step."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")  # lets the dashboard read while the bot writes
    conn.executescript(_SCHEMA)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_message(thread_id: str, role: str, content: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO messages (thread_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (thread_id, role, content, _now()),
        )


def log_tool_call(thread_id: str, tool_name: str, tool_input: dict, tool_output: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO tool_calls (thread_id, tool_name, tool_input, tool_output, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (thread_id, tool_name, json.dumps(tool_input), tool_output, _now()),
        )


def _extract_text(content) -> str:
    """A LangChain message's .content is either a plain string, or (for the
    multimodal case webhook.py builds) a list of content blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
        has_image = any(isinstance(b, dict) and b.get("type") == "image_url" for b in content)
        text = " ".join(p for p in parts if p)
        return f"[image] {text}".strip() if has_image else text
    return str(content)


def log_turn(thread_id: str, new_messages: list) -> None:
    """Log exactly the messages one GRAPH.invoke() call added — pass
    result["messages"][prior_count:], where prior_count is the message
    count from GRAPH.get_state(config) taken *before* invoking. Matches
    each AIMessage's tool_calls to the ToolMessage that follows (by
    tool_call_id) so decode_emi_offer etc. land in tool_calls, not buried
    in message text.
    """
    pending_tool_calls: dict[str, tuple[str, dict]] = {}
    for msg in new_messages:
        if isinstance(msg, HumanMessage):
            log_message(thread_id, "user", _extract_text(msg.content))
        elif isinstance(msg, AIMessage):
            for tc in msg.tool_calls or []:
                pending_tool_calls[tc["id"]] = (tc["name"], tc["args"])
            if msg.content:
                log_message(thread_id, "assistant", _extract_text(msg.content))
        elif isinstance(msg, ToolMessage):
            name, args = pending_tool_calls.pop(msg.tool_call_id, (msg.name or "unknown_tool", {}))
            log_tool_call(thread_id, name, args, _extract_text(msg.content))

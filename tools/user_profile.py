"""Tier-3 memory: a long-term user profile store, independent of any
conversation thread.

This is deliberately a different mechanism from conversational memory
(agent/agent.py's FinanceAgent.messages, or the WhatsApp MVP's LangGraph
checkpointer) — see docs/multi-agent-patterns.md #2 for the full framing.
Those remember *what was said, in this thread*. This remembers *facts
about the user* — income, essential expenses — that should be available
whether or not they were mentioned in the current conversation, and that
persist across every conversation the user will ever have, not just one
thread. agents/budget_agent.py is the one specialist that actually needs
this; credit_debt_agent and markets_agent don't, which is exactly the
point being illustrated.

Plain sqlite3, no ORM — matches whatsapp/storage.py's "two tiny tables is
simple enough" pattern rather than introducing a new persistence style for
one new table.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "profiles.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_profile (
    user_id TEXT NOT NULL,
    field TEXT NOT NULL,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, field)
);
"""


def _get_connection() -> sqlite3.Connection:
    # Reads the module-level DB_PATH at call time (not import time) so
    # tests can monkeypatch tools.user_profile.DB_PATH to a temp file
    # without this module needing to know it's being tested.
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(_SCHEMA)
    return conn


def save_profile_field(user_id: str, field: str, value: str) -> dict:
    """Store or overwrite one durable fact about a user, e.g.
    field="monthly_income", value="90000"."""
    with _get_connection() as conn:
        conn.execute(
            "INSERT INTO user_profile (user_id, field, value, updated_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, field) DO UPDATE SET "
            "value=excluded.value, updated_at=excluded.updated_at",
            (user_id, field, value, datetime.now(timezone.utc).isoformat()),
        )
    return {"saved": field, "value": value}


def get_profile(user_id: str) -> dict:
    """Fetch every saved fact for a user as a flat dict — empty if nothing's
    been saved for them yet (a brand new user, or a fresh test DB)."""
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT field, value FROM user_profile WHERE user_id = ?",
            (user_id,),
        ).fetchall()
    return {field: value for field, value in rows}

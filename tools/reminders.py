"""Proactive reminders: the one capability class nothing else in this repo
has. Every other tool answers a question when asked — this one registers
something to happen *later*, unprompted. This module only owns the data
(when something is due, whether it's already been sent) — it never sends
anything itself, so it stays plain and testable without touching Twilio.
The actual sending — the genuinely new architectural piece, since nothing
in a request/response loop can make FinBuddy speak first — lives in
scheduler/send_reminders.py. See docs/multi-agent-patterns.md for why this
was worth calling out separately from the memory tiers.

Plain sqlite3, same "no ORM, one small table" pattern as user_profile.py
and whatsapp/storage.py.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "reminders.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    message TEXT NOT NULL,
    due_date TEXT NOT NULL,                    -- ISO date, e.g. "2026-09-05"
    recurrence TEXT NOT NULL DEFAULT 'none',   -- 'none' | 'monthly'
    last_sent_date TEXT,                       -- ISO date, NULL if never sent
    created_at TEXT NOT NULL
);
"""


def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(_SCHEMA)
    conn.row_factory = sqlite3.Row
    return conn


def create_reminder(
    user_id: str, message: str, due_date: str, recurrence: str = "none"
) -> dict:
    """Create a reminder. user_id should be whatever the delivery channel
    needs to reach the person later (e.g. "whatsapp:+91..." — matching
    whatsapp/webhook.py's From field, so scheduler/send_reminders.py can
    deliver to it directly). due_date is an ISO date string
    ("YYYY-MM-DD"). recurrence: "none" (fires once) or "monthly" (re-fires
    on roughly the same day each month after being sent)."""
    if recurrence not in ("none", "monthly"):
        return {"error": "recurrence must be 'none' or 'monthly'"}
    try:
        date.fromisoformat(due_date)
    except ValueError:
        return {"error": f"due_date must be YYYY-MM-DD, got {due_date!r}"}

    with _get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO reminders (user_id, message, due_date, recurrence, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, message, due_date, recurrence, datetime.now(timezone.utc).isoformat()),
        )
        reminder_id = cur.lastrowid
    return {"created": True, "reminder_id": reminder_id, "due_date": due_date}


def get_reminders_for_user(user_id: str) -> list[dict]:
    """Every reminder belonging to a user, due or not, sent or not — for
    a UI listing ("my reminders"), not the scheduler's "what's due right
    now" question (that's get_due_reminders below)."""
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM reminders WHERE user_id = ? ORDER BY due_date", (user_id,)
        ).fetchall()
    return [dict(row) for row in rows]


def get_due_reminders(as_of: date | None = None) -> list[dict]:
    """Reminders due on or before `as_of` (default: today) that haven't
    already fired for this cycle. A 'none' reminder that's ever been sent
    never shows again; a 'monthly' one shows again once its (rolled-
    forward, see mark_sent) due_date arrives, but not twice on the same
    day it was just sent."""
    as_of = as_of or date.today()
    as_of_str = as_of.isoformat()
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM reminders WHERE due_date <= ? "
            "AND NOT (recurrence = 'none' AND last_sent_date IS NOT NULL) "
            "AND (last_sent_date IS NULL OR last_sent_date != ?)",
            (as_of_str, as_of_str),
        ).fetchall()
    return [dict(row) for row in rows]


def mark_sent(reminder_id: int, sent_date: date | None = None) -> None:
    """Record that a reminder fired. A 'monthly' reminder's due_date rolls
    forward a month so the next scheduler run schedules it correctly; a
    'none' reminder is left as-is — get_due_reminders excludes any 'none'
    reminder with a non-null last_sent_date permanently, rather than
    relying on date comparison, so it never fires twice.

    Known simplification: the rolled-forward day is clamped to 28 to
    dodge Feb/30-day-month edge cases entirely, rather than implementing
    real "same day next month, or last day if the month is shorter"
    semantics. Fine for a reminder (a day early is harmless); would need
    revisiting for anything date-precision-sensitive.
    """
    sent_date = sent_date or date.today()
    with _get_connection() as conn:
        row = conn.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,)).fetchone()
        if row is None:
            return
        new_due = row["due_date"]
        if row["recurrence"] == "monthly":
            due = date.fromisoformat(row["due_date"])
            month = due.month % 12 + 1
            year = due.year + (1 if due.month == 12 else 0)
            new_due = date(year, month, min(due.day, 28)).isoformat()
        conn.execute(
            "UPDATE reminders SET last_sent_date = ?, due_date = ? WHERE id = ?",
            (sent_date.isoformat(), new_due, reminder_id),
        )

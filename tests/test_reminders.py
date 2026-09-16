"""Deterministic tests for tools/reminders.py — no network, no Twilio, no
scheduler involved. Each test points DB_PATH at a fresh temp file, same
pattern as test_user_profile.py.
"""

from __future__ import annotations

from datetime import date

import tools.reminders as reminders


def test_create_reminder_rejects_bad_recurrence(tmp_path, monkeypatch):
    monkeypatch.setattr(reminders, "DB_PATH", tmp_path / "reminders.db")
    result = reminders.create_reminder("whatsapp:+911234567890", "pay EMI", "2026-09-05", "weekly")
    assert "error" in result


def test_create_reminder_rejects_bad_date(tmp_path, monkeypatch):
    monkeypatch.setattr(reminders, "DB_PATH", tmp_path / "reminders.db")
    result = reminders.create_reminder("whatsapp:+911234567890", "pay EMI", "not-a-date")
    assert "error" in result


def test_due_reminder_is_returned(tmp_path, monkeypatch):
    monkeypatch.setattr(reminders, "DB_PATH", tmp_path / "reminders.db")
    reminders.create_reminder("whatsapp:+911234567890", "pay EMI", "2026-09-01")
    due = reminders.get_due_reminders(as_of=date(2026, 9, 1))
    assert len(due) == 1
    assert due[0]["message"] == "pay EMI"


def test_future_reminder_is_not_yet_due(tmp_path, monkeypatch):
    monkeypatch.setattr(reminders, "DB_PATH", tmp_path / "reminders.db")
    reminders.create_reminder("whatsapp:+911234567890", "pay EMI", "2026-12-25")
    due = reminders.get_due_reminders(as_of=date(2026, 9, 1))
    assert due == []


def test_none_recurrence_never_fires_again_after_being_sent(tmp_path, monkeypatch):
    monkeypatch.setattr(reminders, "DB_PATH", tmp_path / "reminders.db")
    created = reminders.create_reminder("whatsapp:+911234567890", "pay EMI", "2026-09-01")
    reminders.mark_sent(created["reminder_id"], sent_date=date(2026, 9, 1))

    # Even weeks later, a one-off reminder must not resurface.
    due = reminders.get_due_reminders(as_of=date(2026, 9, 20))
    assert due == []


def test_monthly_recurrence_rolls_forward_and_fires_again_next_month(tmp_path, monkeypatch):
    monkeypatch.setattr(reminders, "DB_PATH", tmp_path / "reminders.db")
    created = reminders.create_reminder(
        "whatsapp:+911234567890", "pay EMI", "2026-09-05", recurrence="monthly"
    )
    reminders.mark_sent(created["reminder_id"], sent_date=date(2026, 9, 5))

    # Not due again the same day it was sent, or immediately after.
    assert reminders.get_due_reminders(as_of=date(2026, 9, 5)) == []
    assert reminders.get_due_reminders(as_of=date(2026, 9, 6)) == []

    # But due again once the rolled-forward date (~one month later) arrives.
    due_next_month = reminders.get_due_reminders(as_of=date(2026, 10, 5))
    assert len(due_next_month) == 1
    assert due_next_month[0]["due_date"] == "2026-10-05"


def test_get_reminders_for_user_lists_everything_due_or_not(tmp_path, monkeypatch):
    monkeypatch.setattr(reminders, "DB_PATH", tmp_path / "reminders.db")
    reminders.create_reminder("whatsapp:+911234567890", "past-due EMI", "2026-01-01")
    reminders.create_reminder("whatsapp:+911234567890", "future renewal", "2026-12-25")

    mine = reminders.get_reminders_for_user("whatsapp:+911234567890")
    assert {r["message"] for r in mine} == {"past-due EMI", "future renewal"}
    # A different user's reminders must never leak into this list.
    other = reminders.get_reminders_for_user("whatsapp:+920000000000")
    assert other == []


def test_reminders_are_isolated_per_user(tmp_path, monkeypatch):
    monkeypatch.setattr(reminders, "DB_PATH", tmp_path / "reminders.db")
    reminders.create_reminder("whatsapp:+911111111111", "user A's EMI", "2026-09-01")
    reminders.create_reminder("whatsapp:+922222222222", "user B's EMI", "2026-09-01")

    due = reminders.get_due_reminders(as_of=date(2026, 9, 1))
    user_ids = {r["user_id"] for r in due}
    assert user_ids == {"whatsapp:+911111111111", "whatsapp:+922222222222"}

"""Deterministic tests for scheduler/send_reminders.py — twilio.rest.Client
is monkeypatched so no real message is ever sent and no real Twilio
credentials are needed, same spirit as every other test in this repo that
touches an external service (test_web_research.py mocks httpx.get the
same way).
"""

from __future__ import annotations

from datetime import date

import pytest

import scheduler.send_reminders as send_reminders
import tools.reminders as reminders


class _FakeMessages:
    def __init__(self, calls: list[dict]):
        self._calls = calls

    def create(self, **kwargs):
        self._calls.append(kwargs)


class _FakeClient:
    def __init__(self, *_args, **_kwargs):
        self.calls: list[dict] = []
        self.messages = _FakeMessages(self.calls)


@pytest.fixture(autouse=True)
def _isolated_reminders_db(tmp_path, monkeypatch):
    monkeypatch.setattr(reminders, "DB_PATH", tmp_path / "reminders.db")


@pytest.fixture(autouse=True)
def _fake_twilio_creds(monkeypatch):
    monkeypatch.setattr(send_reminders, "TWILIO_ACCOUNT_SID", "fake_sid")
    monkeypatch.setattr(send_reminders, "TWILIO_AUTH_TOKEN", "fake_token")


def test_raises_clearly_when_twilio_creds_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(send_reminders, "TWILIO_ACCOUNT_SID", None)
    monkeypatch.setattr(send_reminders, "TWILIO_AUTH_TOKEN", None)
    with pytest.raises(RuntimeError):
        send_reminders.send_due_reminders()


def test_sends_and_marks_due_reminders(monkeypatch):
    fake_client_holder: dict[str, _FakeClient] = {}

    def _fake_client_factory(*args, **kwargs):
        client = _FakeClient(*args, **kwargs)
        fake_client_holder["client"] = client
        return client

    monkeypatch.setattr("twilio.rest.Client", _fake_client_factory)

    reminders.create_reminder("whatsapp:+911234567890", "pay your EMI", "2026-09-01")
    results = send_reminders.send_due_reminders(as_of=date(2026, 9, 1))

    assert len(results) == 1
    client = fake_client_holder["client"]
    assert len(client.calls) == 1
    assert client.calls[0]["to"] == "whatsapp:+911234567890"
    assert "pay your EMI" in client.calls[0]["body"]

    # Sent once — a second run the same day must not resend it.
    results_again = send_reminders.send_due_reminders(as_of=date(2026, 9, 1))
    assert results_again == []
    assert len(client.calls) == 1


def test_nothing_due_sends_nothing(monkeypatch):
    monkeypatch.setattr("twilio.rest.Client", lambda *a, **k: _FakeClient())
    results = send_reminders.send_due_reminders(as_of=date(2026, 9, 1))
    assert results == []

"""Deterministic tests for tools/personalized_insights.py — the Groq
client is monkeypatched so no real API call (and no cost) happens in the
default test run, same spirit as every other external-service test in
this repo (test_web_research.py mocks httpx.get, test_scheduler.py mocks
twilio.rest.Client)."""

from __future__ import annotations

import tools.personalized_insights as personalized_insights


class _FakeMessage:
    def __init__(self, content: str):
        self.content = content


class _FakeChoice:
    def __init__(self, content: str):
        self.message = _FakeMessage(content)


class _FakeCompletion:
    def __init__(self, content: str):
        self.choices = [_FakeChoice(content)]


class _FakeChatCompletions:
    def __init__(self, content: str):
        self._content = content

    def create(self, **_kwargs):
        return _FakeCompletion(self._content)


class _FakeChat:
    def __init__(self, content: str):
        self.completions = _FakeChatCompletions(content)


class _FakeGroqClient:
    def __init__(self, *_args, **_kwargs):
        self.chat = _FakeChat("A repo rate hike would raise EMI rates on your existing loans.")


_HEADLINES = [{"title": "RBI raises repo rate by 25bps", "source": "Economic Times", "link": "x"}]


def test_no_headlines_short_circuits_without_calling_the_model():
    result = personalized_insights.synthesize_personalized_update("some situation", [])
    assert "note" in result
    assert "No relevant" in result["note"]


def test_missing_api_key_is_reported_as_data(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    result = personalized_insights.synthesize_personalized_update("some situation", _HEADLINES)
    assert "error" in result


def test_synthesizes_a_note_from_headlines(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake_key")
    monkeypatch.setattr(personalized_insights, "Groq", _FakeGroqClient)
    result = personalized_insights.synthesize_personalized_update(
        "Has 1 active loan, total EMI ₹9,500/month.", _HEADLINES
    )
    assert result["note"] == "A repo rate hike would raise EMI rates on your existing loans."


def test_model_error_is_reported_as_data_not_raised(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake_key")

    class _BrokenClient:
        def __init__(self, *_a, **_k):
            raise RuntimeError("network down")

    monkeypatch.setattr(personalized_insights, "Groq", _BrokenClient)
    result = personalized_insights.synthesize_personalized_update("some situation", _HEADLINES)
    assert "error" in result

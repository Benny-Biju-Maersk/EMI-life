"""Deterministic tests for tools/web_research.py — no real network calls.
httpx.get is monkeypatched to return a fixed fixture, same spirit as
test_tools.py staying runnable with no credentials and no live dependency:
a real news feed's content changes constantly, so asserting against it
directly would make this test flaky by definition, not just slow.
"""

from __future__ import annotations

import httpx
import pytest

import tools.web_research as web_research

_FIXTURE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Google News</title>
    <item>
      <title>Reliance Q3 profit beats estimates - Economic Times</title>
      <link>https://example.com/a</link>
      <pubDate>Mon, 01 Sep 2026 10:00:00 GMT</pubDate>
      <source>Economic Times</source>
    </item>
    <item>
      <title>Reliance announces new retail push - Moneycontrol</title>
      <link>https://example.com/b</link>
      <pubDate>Mon, 01 Sep 2026 09:00:00 GMT</pubDate>
      <source>Moneycontrol</source>
    </item>
    <item>
      <title>Reliance stock reaction to Q3 results - Mint</title>
      <link>https://example.com/c</link>
      <pubDate>Mon, 01 Sep 2026 08:00:00 GMT</pubDate>
      <source>Mint</source>
    </item>
  </channel>
</rss>"""


class _FakeResponse:
    def __init__(self, text: str, status_error: bool = False):
        self.text = text
        self._status_error = status_error

    def raise_for_status(self):
        if self._status_error:
            raise httpx.HTTPStatusError("bad status", request=None, response=self)


def test_empty_query_is_an_error():
    assert "error" in web_research.get_market_news("")
    assert "error" in web_research.get_market_news("   ")


def test_non_positive_max_results_is_an_error():
    assert "error" in web_research.get_market_news("Reliance", max_results=0)


def test_parses_headlines_from_feed(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(_FIXTURE_RSS))
    result = web_research.get_market_news("Reliance Industries")
    assert result["query"] == "Reliance Industries"
    assert result["headline_count"] == 3
    first = result["headlines"][0]
    assert first["title"] == "Reliance Q3 profit beats estimates - Economic Times"
    assert first["link"] == "https://example.com/a"
    assert first["source"] == "Economic Times"


def test_max_results_truncates(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(_FIXTURE_RSS))
    result = web_research.get_market_news("Reliance Industries", max_results=1)
    assert result["headline_count"] == 1


def test_http_error_is_reported_as_data_not_raised(monkeypatch):
    def _raise(*_a, **_k):
        raise httpx.ConnectError("network down")

    monkeypatch.setattr(httpx, "get", _raise)
    result = web_research.get_market_news("Reliance Industries")
    assert "error" in result


def test_malformed_feed_is_reported_as_data_not_raised(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse("not xml at all"))
    result = web_research.get_market_news("Reliance Industries")
    assert "error" in result

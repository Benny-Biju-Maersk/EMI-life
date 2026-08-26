"""Tests for the WhatsApp webhook that never touch Twilio or the LLM —
signature validation and the no-input branch are both fully deterministic.
Live agent replies are exercised manually (see docs/product-brief.md's
verification steps), same reasoning as tests/test_agents.py skipping live
calls: those cost real API credits and hit rate limits, these don't need to.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from whatsapp import webhook

client = TestClient(webhook.app)


def test_no_body_no_media_gets_prompt_reply(monkeypatch):
    monkeypatch.setattr(webhook, "TWILIO_AUTH_TOKEN", None)  # skip signature check
    resp = client.post("/whatsapp", data={"From": "whatsapp:+911234567890"})
    assert resp.status_code == 200
    assert "screenshot" in resp.text.lower()


def test_invalid_signature_rejected(monkeypatch):
    monkeypatch.setattr(webhook, "TWILIO_AUTH_TOKEN", "test-auth-token")
    resp = client.post(
        "/whatsapp",
        data={"From": "whatsapp:+911234567890", "Body": "hi"},
        headers={"X-Twilio-Signature": "not-a-real-signature"},
    )
    assert resp.status_code == 403

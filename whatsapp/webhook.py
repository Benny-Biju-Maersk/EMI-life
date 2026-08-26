"""WhatsApp webhook for the checkout-EMI-trap MVP (Twilio Sandbox).

Run with:
    uvicorn whatsapp.webhook:app --reload

Then tunnel it (e.g. `ngrok http 8000`) and set the tunnel's /whatsapp URL
as the Twilio Sandbox's "when a message comes in" webhook.

Required .env vars (in addition to the existing ANTHROPIC_* ones):
    TWILIO_ACCOUNT_SID   # from the Twilio console
    TWILIO_AUTH_TOKEN    # from the Twilio console — also used to validate
                          # that incoming webhook requests really are from
                          # Twilio, and to fetch protected media URLs

Runs on the LangGraph checkout agent (whatsapp/agent.py) — a single
create_react_agent, not the Phase 2 supervisor/multi-agent split — with a
checkpointer that remembers each sender's conversation across turns, keyed
by their WhatsApp number as the LangGraph `thread_id`.
"""

from __future__ import annotations

import base64
import os

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

load_dotenv()

from whatsapp import storage  # noqa: E402  (after load_dotenv)
from whatsapp.agent import build_whatsapp_agent  # noqa: E402

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")

app = FastAPI(title="FinBuddy WhatsApp webhook")

# Built once at import time, not per-request — see build_whatsapp_agent's
# docstring for why (a fresh MemorySaver per request would lose memory).
GRAPH = build_whatsapp_agent()


async def _request_url(request: Request) -> str:
    """Reconstruct the externally-visible URL Twilio actually posted to, for
    signature validation. Prefers X-Forwarded-* headers since a local dev
    tunnel (ngrok) fronts this as https while uvicorn sees plain http."""
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
    return f"{scheme}://{host}{request.url.path}"


@app.post("/whatsapp")
async def whatsapp_webhook(request: Request) -> Response:
    form = await request.form()
    params = dict(form.items())

    if TWILIO_AUTH_TOKEN:
        validator = RequestValidator(TWILIO_AUTH_TOKEN)
        signature = request.headers.get("x-twilio-signature", "")
        url = await _request_url(request)
        if not validator.validate(url, params, signature):
            return Response(content="invalid signature", status_code=403)
    # else: no TWILIO_AUTH_TOKEN configured yet — skip validation (dev-only
    # convenience for before Twilio env vars are set; don't deploy like this).

    from_number = params.get("From", "unknown")
    body = (params.get("Body") or "").strip()
    num_media = int(params.get("NumMedia", "0") or "0")

    reply_text: str
    try:
        content: str | list[dict] | None = None
        if num_media > 0:
            media_url = params["MediaUrl0"]
            media_type = params.get("MediaContentType0", "image/jpeg")
            async with httpx.AsyncClient() as client:
                media_resp = await client.get(
                    media_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                )
                media_resp.raise_for_status()
            image_b64 = base64.b64encode(media_resp.content).decode("ascii")
            content = [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": image_b64},
                },
                {"type": "text", "text": body or "Please evaluate this EMI/BNPL offer."},
            ]
        elif body:
            content = body
        else:
            reply_text = (
                "Send me a screenshot of the checkout EMI/BNPL offer "
                "(or just describe it) and I'll tell you what it really costs."
            )
            content = None

        if content is not None:
            config = {"configurable": {"thread_id": from_number}}
            prior_state = GRAPH.get_state(config)
            prior_count = len(prior_state.values.get("messages", []))

            result = GRAPH.invoke({"messages": [{"role": "user", "content": content}]}, config=config)
            reply_text = result["messages"][-1].content

            try:
                storage.log_turn(from_number, result["messages"][prior_count:])
            except Exception:
                # Logging is for the dashboard, not the user — never let a
                # storage hiccup turn a successful reply into a failed one.
                pass
    except Exception as e:
        # Never let a bad turn (rate limit, billing hiccup, a malformed
        # image) leave the user with no reply — same philosophy as
        # chat.py's per-turn error handling.
        reply_text = f"Something went wrong on my end ({e}) — try again in a moment."

    twiml = MessagingResponse()
    twiml.message(reply_text)
    return Response(content=str(twiml), media_type="application/xml")

"""The actually-proactive piece.

tools/reminders.py only tracks *when* something is due — nothing sends
anything on its own. Nothing in a request/response loop can either:
agent/agent.py's chat(), any Phase 2 specialist, whatsapp/agent.py's
graph.invoke() — every one of them only ever runs because a message
arrived. Reminders need something to run on a schedule, independent of
any conversation, and decide to speak first. That's this file: put it on
a scheduler (cron, Windows Task Scheduler, a cloud scheduler — anything
that calls it periodically) and it becomes the difference this repo's
architecture doc names between "an LLM you chat with" and a system that
can act without being asked. See docs/multi-agent-patterns.md.

Deliberately not part of whatsapp/webhook.py: that file replies to an
*inbound* Twilio webhook with TwiML. This uses Twilio's REST API to send
a message Twilio never asked for — the Messages resource, not a webhook
reply. Genuinely different Twilio capability, so a separate, small file.

Outside Twilio's Sandbox, WhatsApp's own policy requires an approved
message template for anything sent outside a 24-hour window the user
opened by messaging first — the Sandbox is more permissive for testing.
Don't assume this script works unmodified past Sandbox; see
https://www.twilio.com/docs/whatsapp/tutorial/send-whatsapp-notification-messages-templates
before deploying it for real.

Run with:
    python -m scheduler.send_reminders
"""

from __future__ import annotations

import os
from datetime import date

from dotenv import load_dotenv

from tools.reminders import get_due_reminders, mark_sent

load_dotenv()

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
# Twilio's own shared Sandbox number — same one whatsapp/webhook.py's
# Sandbox setup already sends *replies* from; override via .env once on a
# real WhatsApp Business number.
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")


def send_due_reminders(as_of: date | None = None) -> list[dict]:
    """Check what's due right now and push a WhatsApp message for each.
    Kept separate from __main__ so it's callable (and testable, with the
    Twilio client injected/mocked) without needing to actually run this
    as a script.
    """
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN):
        raise RuntimeError(
            "TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN must be set in .env "
            "(same credentials whatsapp/webhook.py already uses)."
        )
    # Imported here, not at module level, so tests can run (and this
    # module can be imported) without the twilio package's REST client
    # needing real network-capable credentials just to construct.
    from twilio.rest import Client

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    sent = []
    for reminder in get_due_reminders(as_of):
        client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            to=reminder["user_id"],  # e.g. "whatsapp:+91..." — see tools/reminders.py
            body=f"⏰ FinBuddy reminder: {reminder['message']}",
        )
        mark_sent(reminder["id"], as_of)
        sent.append(reminder)
    return sent


if __name__ == "__main__":
    results = send_due_reminders()
    print(f"Sent {len(results)} reminder(s).")

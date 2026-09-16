"""Reminder specialist: the conversational half of the proactive-reminders
feature. This agent only ever REGISTERS intent — "remind me about X on
date Y" — it never sends anything itself, and can't: nothing inside a
request/response loop can make FinBuddy speak first (see
scheduler/send_reminders.py's docstring, the piece that actually does).
This specialist's whole job is being the honest front door to that split:
its system prompt is explicit that creating a reminder here doesn't mean
anything happens right now.

Same create_react_agent pattern as every other specialist in agents/.
"""

from __future__ import annotations

from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from agents.tools import REMINDER_TOOLS

SYSTEM_PROMPT = """You are the Reminder specialist for FinBuddy, a personal
finance assistant for users in India.

Scope: registering future reminders — an EMI due date, a renewal, a
follow-up check-in — NOT answering questions about the user's current
situation (that's other specialists' job).

Rules:
- Use create_reminder_tool whenever the user asks to be reminded about
  something. Always confirm back the exact date and, for a recurring
  reminder, that it repeats monthly.
- Be explicit and honest about what this does: creating a reminder here
  does not send anything right now. It registers something to be
  delivered later, by a separate process, on the date given. If the user
  seems to expect an immediate action, say so plainly rather than letting
  them assume otherwise.
- user_id: always use "default_user" — no per-user identity system exists
  yet in this REPL; a real deployment (e.g. the WhatsApp MVP) would use
  the user's WhatsApp number instead, so the reminder can actually be
  delivered to them. See docs/multi-agent-patterns.md.
- If the user gives a relative date ("next Friday", "in two weeks"),
  convert it to an explicit YYYY-MM-DD before calling the tool — never
  pass a relative phrase through as-is.
- Currency is INR where relevant. Be concise and concrete.
"""


def build_reminder_agent(model: ChatGroq):
    return create_react_agent(
        model,
        tools=REMINDER_TOOLS,
        prompt=SYSTEM_PROMPT,
        name="reminder_agent",
    )

"""LLM-synthesized note connecting real-time news (tools/web_research.py)
to a specific user's saved financial situation
(tools/financial_profile.py / tools/user_profile.py).

The one place in this repo an API endpoint makes an LLM call directly,
rather than routing through a conversational agent (agent/agent.py,
agents/*, whatsapp/agent.py): this is a single, stateless synthesis step
— given some headlines and a one-line situation summary, write 2-4
sentences — not a multi-turn conversation. Pulling in LangGraph or a
create_react_agent for one non-conversational call would be more
machinery than the job needs; a direct `groq` SDK call (same library
Phase 1's agent/agent.py already runs on) is the right amount for what
this does.

Informational only — same SEBI-line constraint as agents/research_agent.py
and markets_agent.py: this explains why a headline might matter to
someone in this situation, never what to do about it.
"""

from __future__ import annotations

import os

from groq import Groq

MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

SYSTEM_PROMPT = """You explain how real-world financial news might matter
to a specific person's situation, given a one-line summary of their loans/
savings/income and a handful of real headlines.

Rules:
- Reference the headlines given to you; never invent one or recall one
  from memory.
- Never recommend a specific stock, fund, lender, or action ("you should
  buy/sell/switch to/refinance with X"). Explain relevance and mechanism
  only — e.g. "a repo rate hike would raise EMI rates on your existing
  loans," not "you should prepay now."
- 2-4 sentences, concrete, no filler. Currency INR.
- This is financial information, not personalized investment or credit
  advice, and you are not a SEBI-registered adviser.
"""


def synthesize_personalized_update(profile_summary: str, headlines: list[dict]) -> dict:
    """profile_summary: a short, human-readable line like "Has 2 active
    loans, total EMI ₹18,500/month, monthly income ₹90,000." headlines:
    the list tools/web_research.py:get_market_news returns."""
    if not headlines:
        return {"note": "No relevant recent news found to connect to your situation right now."}

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return {"error": "GROQ_API_KEY not configured"}

    headline_text = "\n".join(
        f"- {h.get('title', '')} ({h.get('source', 'unknown source')})" for h in headlines
    )
    try:
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model=MODEL,
            max_tokens=300,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Situation: {profile_summary}\n\nRecent headlines:\n{headline_text}",
                },
            ],
        )
        return {"note": resp.choices[0].message.content}
    except Exception as e:
        # Same "never let a tool crash the caller" convention as every
        # other tool in this repo (see docs/decision.md #3) — a synthesis
        # failure is data the caller can show gracefully, not an exception.
        return {"error": f"could not synthesize update: {e}"}

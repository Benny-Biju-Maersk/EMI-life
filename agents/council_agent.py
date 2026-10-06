"""Wraps agents/council.py's debate/consensus pattern as a specialist the
supervisor can route to like any other — the "subagent-as-tool" pattern
this repo already uses for handoffs (langgraph_supervisor's own
transfer_to_<agent> tools), just with the "agent" being a multi-model
council instead of a single ReAct loop.

This agent's own model only has one job: call consult_council_tool and
relay its result faithfully (including disagreement between panelists) —
it doesn't re-reason over the question itself, that's what the council
already did. Kept as a real create_react_agent (not a bare function node)
so it slots into `agents=[...]` in orchestrator.py exactly like every
other specialist, with no special-casing in the supervisor's graph wiring.
"""

from __future__ import annotations

import json

from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from agents.council import run_council

SYSTEM_PROMPT = """You are the Council specialist for FinBuddy, a personal
finance assistant for users in India.

Scope: genuinely high-stakes or subjective money decisions — "should I
take this loan", "is this a good idea" — where showing that reasonable
models can disagree is more honest than a single confident verdict. NOT
for anything with a deterministic right answer (EMI math, a stock price) —
those are other specialists' job and don't need a council.

Rules:
- Always call consult_council_tool for anything routed to you — you do
  not answer from your own reasoning, the council already did that
  independently across several models.
- Relay the synthesis faithfully. If the council names disagreement
  between panelists, keep that in your answer — don't smooth it over into
  a single confident line.
- Pass along whatever numeric context the user already gave (income,
  existing EMIs, item price) as `context` so every panelist reasons from
  the same facts.
- Currency is INR. You provide financial INFORMATION and EDUCATION, not
  personalized investment advice.
"""


@tool
async def consult_council_tool(question: str, context: dict | None = None) -> str:
    """Get an independent, multi-model council opinion on a high-stakes or
    subjective money question, synthesized into one answer that names any
    real disagreement between the panelists. Slower and more expensive
    than a single specialist call (several models run in parallel, plus a
    synthesis call) — use it for judgment calls, not routine math.

    Args:
        question: The decision or question to put to the council.
        context: Optional known facts (e.g. monthly_net_income,
            existing_emis, item_price) so every panelist reasons from the
            same numbers instead of guessing.
    """
    result = await run_council(question, context)
    return json.dumps(result)


def build_council_agent(model: ChatGroq):
    return create_react_agent(
        model,
        tools=[consult_council_tool],
        prompt=SYSTEM_PROMPT,
        name="council_agent",
    )

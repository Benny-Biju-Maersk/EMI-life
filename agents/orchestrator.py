"""Supervisor graph wiring every Phase-2 specialist together, including the
council (agents/council.py) and MCP-backed research tools
(agents/mcp_tools.py).

This is the multi-agent equivalent of agent/agent.py's chat loop: instead of
one system prompt deciding which of four tools to call, a supervisor LLM
decides which *specialist agent* to hand the conversation to. Each specialist
is itself a small ReAct agent (see credit_debt_agent.py / markets_agent.py)
with its own scoped prompt and tools — the "subagent-as-tool" pattern named
in the README roadmap, here supplied by langgraph_supervisor rather than
hand-rolled.

**This graph must be invoked async** (`await graph.ainvoke(...)` /
`async for chunk in graph.astream(...)`), never `.invoke()`/`.stream()` —
research_agent carries MCP tools that only expose an async interface (see
agents/mcp_tools.py), and council_agent's tool is async too (it runs
several models in parallel via asyncio.gather). chat.py's REPL and
api/main.py's endpoints are both async for this reason.

Call build_graph() to get a compiled, invokable graph:

    graph = build_graph()
    result = await graph.ainvoke({"messages": [{"role": "user", "content": "..."}]})
"""

from __future__ import annotations

import asyncio
import os

from langchain_groq import ChatGroq
from langgraph_supervisor import create_supervisor

from agents.budget_agent import build_budget_agent
from agents.council_agent import build_council_agent
from agents.credit_debt_agent import build_credit_debt_agent
from agents.mcp_tools import get_mcp_tools
from agents.markets_agent import build_markets_agent
from agents.reminder_agent import build_reminder_agent
from agents.research_agent import build_research_agent

MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

SUPERVISOR_PROMPT = """You are the supervisor for FinBuddy, a personal
finance assistant for users in India. You do not answer finance questions
yourself — you route each request to the right specialist:

- credit_debt_agent: one-off EMI/loan math, prepayment impact, purchase
  affordability computed from numbers given this turn ("can I afford X",
  "what's my EMI", "should I prepay").
- markets_agent: current stock/market prices ("what's X trading at").
- budget_agent: the user's ongoing month-to-month picture — remembering
  their income/expenses across conversations, not just this one ("what's
  my budget like", "remember my income is X", "am I in good shape
  financially").
- research_agent: real-time news, background context, and FinBuddy's own
  stable knowledge (FOIR rules, what "no-cost EMI" hides, credit score
  factors, the SEBI-RIA line) — "what's happening with X", "any news on
  X", or "why can't you just tell me which stock to buy". Not a price
  lookup (that's markets_agent) and never a buy/sell recommendation.
- reminder_agent: registering a future reminder — "remind me to pay my
  EMI on the 5th", "remind me every month about X". Not for answering
  questions about the user's current situation.
- council_agent: a genuinely high-stakes or subjective judgment call —
  "should I take this loan", "is this a good idea" — where showing that
  independent models can disagree is more honest than a single confident
  verdict from you or one specialist. Not for anything with a
  deterministic right answer (EMI math, a stock price) — route those to
  credit_debt_agent/markets_agent instead; the council is slower and more
  expensive for no benefit on questions that already have one right
  answer.

Hand off to exactly one specialist per request unless the user's question
genuinely spans more than one (e.g. "can I afford X after this stock drop,
and why did it drop" spans markets_agent + research_agent) — in that case
call more than one and combine their answers. Never invent numbers or
headlines yourself.
"""


def build_graph():
    # timeout/max_retries above the SDK's own defaults (30s/2): this
    # machine's network occasionally shows several-second latency on a
    # *cold* TLS connection to a new host (same family of issue as the
    # corporate TLS-interception quirk already documented for direct
    # Anthropic calls) — the default 2 retries weren't enough headroom to
    # ride it out, seen as a bare `groq.APIConnectionError: Connection
    # error.` on the very first call in a fresh process, succeeding
    # immediately on retry. Bumping both rather than guessing which alone
    # would fix it.
    model = ChatGroq(model=MODEL, max_tokens=1500, timeout=60.0, max_retries=5)  # matches agent/agent.py's cap

    # MCP tools loaded once per process, here at build time — before any
    # event loop is running yet (chat.py/api/main.py both call build_graph()
    # at startup), same "build once per process" reasoning as
    # whatsapp/agent.py's checkpointer. See agents/mcp_tools.py for why
    # this needs asyncio.run() rather than a plain call.
    mcp_tools = asyncio.run(get_mcp_tools())

    credit_debt_agent = build_credit_debt_agent(model)
    markets_agent = build_markets_agent(model)
    budget_agent = build_budget_agent(model)
    research_agent = build_research_agent(model, mcp_tools)
    reminder_agent = build_reminder_agent(model)
    council_agent = build_council_agent(model)

    supervisor = create_supervisor(
        agents=[
            credit_debt_agent,
            markets_agent,
            budget_agent,
            research_agent,
            reminder_agent,
            council_agent,
        ],
        model=model,
        prompt=SUPERVISOR_PROMPT,
    )
    return supervisor.compile()

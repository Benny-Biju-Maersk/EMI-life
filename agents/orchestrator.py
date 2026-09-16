"""Supervisor graph wiring the Credit/Debt and Markets specialists together.

This is the multi-agent equivalent of agent/agent.py's chat loop: instead of
one system prompt deciding which of four tools to call, a supervisor LLM
decides which *specialist agent* to hand the conversation to. Each specialist
is itself a small ReAct agent (see credit_debt_agent.py / markets_agent.py)
with its own scoped prompt and tools — the "subagent-as-tool" pattern named
in the README roadmap, here supplied by langgraph_supervisor rather than
hand-rolled.

Call build_graph() to get a compiled, invokable graph:

    graph = build_graph()
    result = graph.invoke({"messages": [{"role": "user", "content": "..."}]})
"""

from __future__ import annotations

import os

from langchain_groq import ChatGroq
from langgraph_supervisor import create_supervisor

from agents.budget_agent import build_budget_agent
from agents.credit_debt_agent import build_credit_debt_agent
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
- research_agent: real-time news/context — "what's happening with X",
  "any news on X", or the reason behind a price move. Not a price lookup
  (that's markets_agent) and never a buy/sell recommendation.
- reminder_agent: registering a future reminder — "remind me to pay my
  EMI on the 5th", "remind me every month about X". Not for answering
  questions about the user's current situation.

Hand off to exactly one specialist per request unless the user's question
genuinely spans more than one (e.g. "can I afford X after this stock drop,
and why did it drop" spans markets_agent + research_agent) — in that case
call more than one and combine their answers. Never invent numbers or
headlines yourself.
"""


def build_graph():
    model = ChatGroq(model=MODEL, max_tokens=1500)  # matches agent/agent.py's cap
    credit_debt_agent = build_credit_debt_agent(model)
    markets_agent = build_markets_agent(model)
    budget_agent = build_budget_agent(model)
    research_agent = build_research_agent(model)
    reminder_agent = build_reminder_agent(model)

    supervisor = create_supervisor(
        agents=[
            credit_debt_agent,
            markets_agent,
            budget_agent,
            research_agent,
            reminder_agent,
        ],
        model=model,
        prompt=SUPERVISOR_PROMPT,
    )
    return supervisor.compile()

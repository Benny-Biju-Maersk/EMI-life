"""Credit/Debt specialist: EMI math, prepayment impact, purchase affordability.

Built with langgraph.prebuilt.create_react_agent — a prebuilt ReAct loop
(reason -> call tool -> observe -> repeat) equivalent in spirit to the
hand-rolled loop in agent/agent.py, just supplied by the framework instead
of written out by hand.
"""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

from agents.tools import CREDIT_DEBT_TOOLS

SYSTEM_PROMPT = """You are the Credit/Debt specialist for FinBuddy, a personal
finance assistant for users in India.

Scope: EMI and loan math, prepayment impact, and purchase affordability.
Rules:
- Use tools for any calculation. Never do EMI math in your head.
- If you need the user's income or existing EMIs for an affordability check,
  ask for them before calling the tool.
- Currency is INR unless the user says otherwise. Be concise and concrete.
- You provide financial INFORMATION and EDUCATION, not personalized advice.
"""


def build_credit_debt_agent(model: ChatAnthropic):
    return create_react_agent(
        model,
        tools=CREDIT_DEBT_TOOLS,
        prompt=SYSTEM_PROMPT,
        name="credit_debt_agent",
    )

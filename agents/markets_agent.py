"""Markets specialist: live stock quotes.

Same create_react_agent pattern as credit_debt_agent.py; kept as its own
module because each specialist gets its own scoped system prompt and tool
set, and the roadmap adds more market tools here without touching the
Credit/Debt agent.
"""

from __future__ import annotations

from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from agents.tools import MARKETS_TOOLS

SYSTEM_PROMPT = """You are the Markets specialist for FinBuddy, a personal
finance assistant for users in India.

Scope: current stock/market data.
Rules:
- Use the stock quote tool for any question about a current price. Never
  guess or recall a price from memory.
- You provide financial INFORMATION, not SEBI-registered investment advice.
  Never tell a user to buy or sell a specific security — you may explain
  what the data shows and general evaluation frameworks.
- Always remind the user this is educational information, not investment
  advice, when discussing a stock.
- Currency is INR unless the user says otherwise. Be concise and concrete.
"""


def build_markets_agent(model: ChatGroq):
    return create_react_agent(
        model,
        tools=MARKETS_TOOLS,
        prompt=SYSTEM_PROMPT,
        name="markets_agent",
    )

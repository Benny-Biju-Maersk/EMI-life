"""Research specialist: real-time web news — the first specialist in this
repo whose tool reaches outside the process over the network, rather than
computing from given numbers (credit_debt_agent) or reading a local store
(budget_agent). Added as a hands-on multi-agent learning exercise (see
docs/multi-agent-patterns.md) and as groundwork toward the informational
stock analyzer scoped — not yet built — in docs/product-brief.md.

Same create_react_agent pattern as every other specialist in agents/.
"""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

from agents.tools import RESEARCH_TOOLS

SYSTEM_PROMPT = """You are the Research specialist for FinBuddy, a personal
finance assistant for users in India.

Scope: real-time financial/market news via get_market_news_tool — what's
currently being reported about a stock, sector, or economic topic. This is
different from the Markets specialist: that one fetches a live price
number; you fetch live reporting/context, not a number.

Rules:
- Use get_market_news_tool for any question about recent news, "what's
  happening with X", or the context behind a price move. Never invent a
  headline or recall one from memory — always fetch.
- You report what's being reported. Never turn a headline into a buy/sell
  recommendation or a "you should invest" verdict. If asked to do that,
  decline and explain you provide information, not personalized
  investment advice (not SEBI-registered) — same rule the Markets
  specialist follows.
- Cite the source and headline plainly; don't editorialize on direction.
- Currency is INR. Be concise and concrete.
"""


def build_research_agent(model: ChatAnthropic):
    return create_react_agent(
        model,
        tools=RESEARCH_TOOLS,
        prompt=SYSTEM_PROMPT,
        name="research_agent",
    )

"""Tests for the Phase-2 multi-agent orchestrator.

The structural test never touches the network. The live test makes one real
call through the full supervisor -> credit_debt_agent -> tool path and is
skipped automatically if no GROQ_API_KEY is configured (.env or env),
same spirit as tests/test_tools.py staying runnable with no credentials.

The graph is invoked via asyncio.run(graph.ainvoke(...)), not a bare
graph.invoke(...) — see agents/orchestrator.py's docstring: research_agent
carries MCP tools and council_agent's tool is async-only, so this graph's
contract is async invocation even though this particular test's path
(credit_debt_agent, plain sync tools) would likely still work either way.
"""

from __future__ import annotations

import asyncio
import os

import pytest
from dotenv import load_dotenv

load_dotenv()

from agents.orchestrator import build_graph  # noqa: E402  (after load_dotenv)

pytestmark = pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"), reason="no GROQ_API_KEY configured"
)


def test_graph_builds_with_expected_nodes():
    graph = build_graph()
    nodes = set(graph.nodes.keys())
    assert {
        "supervisor",
        "credit_debt_agent",
        "markets_agent",
        "budget_agent",
        "research_agent",
        "reminder_agent",
        "council_agent",
    } <= nodes


def test_credit_question_routes_to_credit_debt_agent():
    graph = build_graph()
    result = asyncio.run(
        graph.ainvoke(
            {"messages": [{"role": "user", "content": "What's the EMI on a 5 lakh loan at 10% for 24 months?"}]}
        )
    )
    names = [getattr(m, "name", None) for m in result["messages"]]
    assert "credit_debt_agent" in names
    reply = result["messages"][-1].content
    assert any(ch.isdigit() for ch in reply)

"""The web portal's agent graph — the full supervisor (every specialist,
the council, MCP tools) wired to persistent per-user memory, the same way
whatsapp/agent.py wires its single checkout agent to a checkpointer.

Why this is its own module instead of just calling agents/orchestrator.py's
build_graph() directly from api/main.py: build_graph() returns a fresh,
memory-less compiled graph — exactly right for chat.py's one-process-one-
session REPL, wrong for a web backend serving many users across many
requests. This module adds the one thing build_graph() deliberately
doesn't own: a checkpointer keyed by user id, built once per process and
reused, same "build once, not per-request" reasoning as
whatsapp/agent.py:build_whatsapp_agent().

Keyed by Clerk user id (e.g. "user_2abc...") as the LangGraph `thread_id`
instead of a WhatsApp number — same mechanism, different identity source.
Backed by data/finbuddy.db, the same file whatsapp/agent.py's checkpointer
and whatsapp/storage.py already share (different tables — LangGraph
manages its own checkpoints/writes schema, so this coexists without
touching either).

Must be invoked async (`await GRAPH.ainvoke(...)`) — see
agents/orchestrator.py's docstring for why (MCP tools, the council).
"""

from __future__ import annotations

import aiosqlite
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph_supervisor import create_supervisor

from agents.budget_agent import build_budget_agent
from agents.council_agent import build_council_agent
from agents.credit_debt_agent import build_credit_debt_agent
from agents.mcp_tools import get_mcp_tools
from agents.markets_agent import build_markets_agent
from agents.orchestrator import MODEL, SUPERVISOR_PROMPT
from agents.reminder_agent import build_reminder_agent
from agents.research_agent import build_research_agent
from whatsapp.storage import DB_PATH

load_dotenv()  # self-contained, same as whatsapp/agent.py


async def build_web_graph():
    """Build once per process — api/main.py awaits this from a FastAPI
    `lifespan` startup hook (async-native), not at bare module-import time
    the way whatsapp/webhook.py's `GRAPH = build_whatsapp_agent()` does,
    because this function is itself async (get_mcp_tools() must be
    awaited, not wrapped in `asyncio.run()`, since a caller already running
    inside an event loop — exactly what a FastAPI app is — can't nest
    another `asyncio.run()` inside it). Reused across every request either
    way — rebuilding per-request would open a fresh sqlite3 connection and
    re-fetch MCP tools over stdio for no reason.
    """
    # AsyncSqliteSaver, not whatsapp/agent.py's plain SqliteSaver — that one
    # only supports sync checkpoint methods (its graph is invoked via
    # .invoke(), never needs async) and raises NotImplementedError under
    # .ainvoke(), which this graph requires (see module docstring).
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(DB_PATH)
    checkpointer = AsyncSqliteSaver(conn)
    await checkpointer.setup()

    model = ChatGroq(model=MODEL, max_tokens=1500, timeout=60.0, max_retries=5)
    mcp_tools = await get_mcp_tools()

    supervisor = create_supervisor(
        agents=[
            build_credit_debt_agent(model),
            build_markets_agent(model),
            build_budget_agent(model),
            build_research_agent(model, mcp_tools),
            build_reminder_agent(model),
            build_council_agent(model),
        ],
        model=model,
        prompt=SUPERVISOR_PROMPT,
    )
    return supervisor.compile(checkpointer=checkpointer)


async def ask(graph, user_id: str, message: str) -> dict:
    """One turn for one signed-in user, memory carried across calls by
    `user_id` as the LangGraph thread_id. Returns the full result state
    (api/main.py picks out what each endpoint needs) rather than just the
    reply text, so a caller can also see which specialist handled it —
    same transparency chat.py's printed trace gives the REPL.
    """
    config = {"configurable": {"thread_id": user_id}}
    return await graph.ainvoke({"messages": [{"role": "user", "content": message}]}, config=config)

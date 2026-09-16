"""The checkout-EMI-trap agent, built on LangGraph instead of the hand-rolled
Phase-1 loop — the piece of Phase 2's work that's actually reused.

Not the supervisor/multi-agent split from agents/orchestrator.py: this is a
single langgraph.prebuilt.create_react_agent, same pattern as
agents/credit_debt_agent.py, carrying CHECKOUT_TOOLS
(agents/tools.py) instead of the Credit/Debt specialist's set. A supervisor
wasn't worth it for one narrow job with three tools.

The actual reason to prefer this over agent/agent.py's loop here: a
checkpointer. Each WhatsApp sender becomes a `thread_id`, and the
checkpointer remembers that thread's full message history across turns
*and* across requests — replacing the hand-rolled `SESSIONS: dict[str,
FinanceAgent]` webhook.py used to keep in-process. Backed by SqliteSaver
(same data/finbuddy.db file whatsapp/storage.py logs to, different table —
LangGraph manages its own schema), so this now survives a restart too, not
just a request.

Model note: this is the one place in the repo that reads GROQ_VISION_MODEL
instead of GROQ_MODEL — this agent's whole job is reading a forwarded
checkout screenshot, and the text-only models used elsewhere (e.g.
openai/gpt-oss-120b) can't see images at all. Needs a vision-capable Groq
model (default: a Qwen3 checkpoint that supports both image input and tool
calls — confirmed live 2026-09-05) instead.
"""

from __future__ import annotations

import os
import sqlite3

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import create_react_agent

from agents.tools import CHECKOUT_TOOLS
from whatsapp.prompts import CHECKOUT_SYSTEM_PROMPT
from whatsapp.storage import DB_PATH

load_dotenv()  # self-contained, same as agent/agent.py — safe to import this
                # module standalone rather than relying on webhook.py's call

MODEL = os.environ.get("GROQ_VISION_MODEL", "qwen/qwen3.6-27b")


def build_whatsapp_agent():
    """Build once per process (webhook.py does this at import time) and
    reuse across requests — rebuilding per-request would create a fresh
    sqlite3 connection each time; cheap but pointless to redo per message."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    checkpointer.setup()

    model = ChatGroq(model=MODEL, max_tokens=1500)
    return create_react_agent(
        model,
        tools=CHECKOUT_TOOLS,
        prompt=CHECKOUT_SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )

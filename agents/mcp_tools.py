"""MCP tool loading for the research/council path — the only agents that
get external MCP tools. `agents/budget_agent.py`, `credit_debt_agent.py`,
`reminder_agent.py` already do their whole job with local DB reads/writes
and pure math; an MCP server wouldn't add anything there, so they don't
get one — this isn't "wire MCP into everything," it's "wire it in where a
specific capability gap exists."

Both servers run as `uvx <package>` subprocesses — isolated, on-demand
environments `uv` manages — rather than being `pip install`ed into this
project's own venv. That's deliberate, not incidental: installing either
package directly into this venv is exactly what happened first, and it
pulled in a newer `mcp` SDK / `starlette` combo that broke `fastapi`
(see requirements.txt's comment on the `fastapi>=0.140` floor). Running
them via `uvx` keeps their dependencies fully out of this venv.

- **mcp-server-fetch** — the official Anthropic reference MCP server
  (github.com/modelcontextprotocol/servers), no API key. Fetches a URL,
  returns cleaned text. Gives research_agent a way to read the *full
  text* behind a headline `get_market_news_tool` found, not just the
  headline string.
- **free-search-mcp** (github.com/sweetcornna/free-search-mcp) —
  local-first, no-API-key, multi-engine web search (DuckDuckGo, Mojeek,
  Startpage, and more). For anything broader than recent news — e.g. "what
  does LazyPay usually charge as a processing fee" — that neither
  `get_market_news_tool` (news-only) nor `tools/knowledge.py` (FinBuddy's
  own static, curated facts) would have. Smaller/less-established project
  than mcp-server-fetch; if it ever stops installing cleanly, swap in
  `open-websearch` (github.com/aas-ee/open-websearch), the fallback named
  when this was proposed.

**Every caller of `get_mcp_tools()` must be async** — MCP is JSON-RPC over
stdio, so `langchain-mcp-adapters` only exposes an async interface. Use
`.ainvoke()`/`.astream()` on any graph carrying these tools, never
`.invoke()`/`.stream()`. `agents/orchestrator.py:build_graph()` fetches
these once (via `asyncio.run`, at process-startup import time, before any
event loop is running — same "build once per process" reasoning as
`whatsapp/agent.py`'s checkpointer) rather than on every request.
"""

from __future__ import annotations

import os
import shutil
import sysconfig
from pathlib import Path

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient


def _find_uvx() -> str:
    """`shutil.which` alone isn't reliable here: `pip install uv` (see
    requirements.txt) put `uvx`/`uvx.exe` in the current user's *site*
    Scripts directory (sysconfig's "<os>_user" scheme —
    `...\\AppData\\Roaming\\Python\\Python314\\Scripts` on this machine),
    which pip itself warns isn't on PATH, and genuinely isn't in a fresh
    shell or under pytest's subprocess environment — confirmed by this
    failing silently (falling back to no MCP tools) under `pytest` despite
    working fine in an interactive terminal. Check PATH first (respects a
    venv or a machine where uv really is on PATH), then fall back to the
    user-scheme Scripts dir before giving up and returning the bare name
    (subprocess creation will raise a clear FileNotFoundError if that's
    still wrong, rather than this function guessing further)."""
    found = shutil.which("uvx")
    if found:
        return found
    scheme = f"{os.name}_user"
    candidate = Path(sysconfig.get_path("scripts", scheme)) / ("uvx.exe" if os.name == "nt" else "uvx")
    return str(candidate) if candidate.exists() else "uvx"


_UVX = _find_uvx()

_CLIENT = MultiServerMCPClient(
    {
        "fetch": {"command": _UVX, "args": ["mcp-server-fetch"], "transport": "stdio"},
        "search": {"command": _UVX, "args": ["free-search-mcp"], "transport": "stdio"},
    }
)


async def get_mcp_tools() -> list[BaseTool]:
    """Every tool from both configured MCP servers, as LangChain
    `BaseTool` instances `create_react_agent` can use directly alongside
    ordinary `@tool`-wrapped functions. Returns an empty list (never
    raises) if a server fails to start — e.g. `uvx`/network unavailable —
    so a broken MCP server degrades the research agent to its existing
    tools instead of taking the whole graph down at startup.
    """
    try:
        return await _CLIENT.get_tools()
    except Exception as e:
        print(f"  [mcp] could not load MCP tools, continuing without them: {e}")
        return []

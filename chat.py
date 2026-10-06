"""Terminal chat with the Phase-2 multi-agent orchestrator.

Same job as main.py, but drives the LangGraph supervisor graph
(agents/orchestrator.py) instead of the single hand-rolled agent — routes
each message to a specialist (or the council) and prints every
handoff/tool call along the way, same transparency main.py's `[tool] ...`
line gives for Phase 1.

Async top-to-bottom (`asyncio.run(main())`, `graph.astream(...)`) — not a
style choice, a requirement: agents/orchestrator.py's graph carries MCP
tools and the council's consult tool, both async-only (see
agents/mcp_tools.py and agents/council_agent.py for why).

Usage:
    export GROQ_API_KEY=gsk_...   # or set in .env
    python chat.py
"""

from __future__ import annotations

import asyncio
import sys

from dotenv import load_dotenv

load_dotenv()

from agents.orchestrator import build_graph  # noqa: E402  (after load_dotenv)


def _print_trace(chunk: dict) -> None:
    """Print each node's activity as the graph streams, so routing and tool
    calls stay visible instead of hidden inside the framework."""
    for node_name, node_output in chunk.items():
        messages = node_output.get("messages", []) if isinstance(node_output, dict) else []
        for msg in messages:
            msg_type = getattr(msg, "type", "")
            if msg_type == "tool":
                tool_name = getattr(msg, "name", "?")
                print(f"  [{node_name}] tool result <- {tool_name}")
            elif msg_type == "ai":
                tool_calls = getattr(msg, "tool_calls", None) or []
                for call in tool_calls:
                    print(f"  [{node_name}] -> {call.get('name')}({call.get('args')})")


async def main():
    graph = build_graph()
    print("FinBuddy (multi-agent) — Ctrl+C or 'quit' to exit.\n")
    messages: list[dict] = []
    while True:
        try:
            user = await asyncio.to_thread(input, "you > ")
            user = user.strip()
        except (KeyboardInterrupt, EOFError):
            print()
            sys.exit(0)
        if not user:
            continue
        if user.lower() in {"quit", "exit"}:
            break

        messages.append({"role": "user", "content": user})
        try:
            final_state = None
            async for chunk in graph.astream({"messages": messages}):
                _print_trace(chunk)
                final_state = chunk

            # Pull the full updated message list from whichever node ran last.
            last_output = next(iter(final_state.values()))
            messages = last_output["messages"]
            reply = messages[-1].content
            print(f"\nfinbuddy > {reply}\n")
        except Exception as e:
            # Never let one bad turn (a rate limit, a billing hiccup, a
            # transient network error) kill the whole REPL — drop the
            # unanswered turn so the next question starts from clean
            # context, and keep the session alive.
            messages.pop()
            print(f"\n  [error] {e}\n  (that turn wasn't recorded — try again)\n")


if __name__ == "__main__":
    asyncio.run(main())

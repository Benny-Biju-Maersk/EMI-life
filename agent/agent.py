"""The agent loop.

This ~80-line loop IS agentic development in miniature:
  1. Send conversation + tool schemas to the model
  2. If the model requests tool calls, execute them and append results
  3. Repeat until the model responds with plain text
Everything else (multi-agent, LangGraph, MCP) is elaboration on this loop.
"""

from __future__ import annotations

import json
import os

from anthropic import Anthropic
from dotenv import load_dotenv

from tools.finance_tools import TOOL_FUNCTIONS
from tools.schemas import TOOL_SCHEMAS

load_dotenv()  # picks up ANTHROPIC_API_KEY / ANTHROPIC_BASE_URL / ANTHROPIC_MODEL from .env

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

SYSTEM_PROMPT = """You are FinBuddy, a personal finance assistant for users in India.

Scope: EMI and loan math, purchase affordability, credit score education,
credit card usage guidance, stock market information, passive income options,
and general money management.

Rules:
- Use tools for any calculation or live data. Never do EMI math in your head.
- If you need the user's income or existing EMIs for an affordability check,
  ask for them before calling the tool.
- You provide financial INFORMATION and EDUCATION, not personalized investment
  advice. Never tell a user to buy or sell a specific security. You may explain
  what a stock's data shows and general evaluation frameworks.
- For anything involving stocks or market-linked products, remind the user
  that this is educational information, not SEBI-registered investment advice.
- Currency is INR unless the user says otherwise. Be concise and concrete.
"""


class FinanceAgent:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        system_prompt: str | None = None,
    ):
        # base_url lets this point at an Anthropic-compatible gateway (e.g.
        # OpenRouter's /api/v1) instead of api.anthropic.com directly.
        self.client = Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
            base_url=base_url or os.environ.get("ANTHROPIC_BASE_URL"),
        )
        # system_prompt lets a different persona (e.g. whatsapp/prompts.py's
        # checkout-moment prompt) reuse this same loop instead of forking it.
        self.system_prompt = system_prompt or SYSTEM_PROMPT
        self.messages: list[dict] = []

    def _execute_tool(self, name: str, tool_input: dict) -> str:
        fn = TOOL_FUNCTIONS.get(name)
        if fn is None:
            return json.dumps({"error": f"unknown tool {name}"})
        try:
            return json.dumps(fn(**tool_input))
        except Exception as e:
            # Return errors to the model as data — it will recover or explain.
            return json.dumps({"error": str(e)})

    def chat(self, user_message: str | list[dict], max_tool_rounds: int = 8) -> str:
        # A plain string becomes a normal text turn, same as always. A list
        # of content blocks (e.g. an image block + a text block, built by
        # whatsapp/webhook.py for a forwarded screenshot) is passed through
        # as-is — the Anthropic API accepts either shape for "content".
        self.messages.append({"role": "user", "content": user_message})

        for _ in range(max_tool_rounds):
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=1500,
                system=self.system_prompt,
                tools=TOOL_SCHEMAS,
                messages=self.messages,
            )

            # Append the assistant turn exactly as returned (may mix text + tool_use)
            self.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                return "".join(b.text for b in response.content if b.type == "text")

            # Execute every tool call in this turn and send results back
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  [tool] {block.name}({json.dumps(block.input)})")
                    result = self._execute_tool(block.name, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )
            self.messages.append({"role": "user", "content": tool_results})

        return "I hit the tool-call limit for one turn — try breaking the question down."

"""The agent loop.

This ~80-line loop IS agentic development in miniature:
  1. Send conversation + tool schemas to the model
  2. If the model requests tool calls, execute them and append results
  3. Repeat until the model responds with plain text
Everything else (multi-agent, LangGraph, MCP) is elaboration on this loop.

Runs on Groq's OpenAI-compatible Chat Completions API (via the `groq`
SDK) — a system prompt is a "system" message in `messages`, not a separate
top-level param the way Anthropic's Messages API takes it, and a tool call
comes back as `message.tool_calls` rather than `tool_use` content blocks.
"""

from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from groq import Groq

from tools.finance_tools import TOOL_FUNCTIONS
from tools.schemas import GROQ_TOOL_SCHEMAS

load_dotenv()  # picks up GROQ_API_KEY / GROQ_MODEL from .env

MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

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
        system_prompt: str | None = None,
    ):
        # timeout/max_retries above the SDK defaults: see
        # agents/orchestrator.py's comment on ChatGroq for why (a cold-TLS-
        # connection latency this network occasionally shows, exceeding
        # the SDK's default 2-retry headroom).
        self.client = Groq(
            api_key=api_key or os.environ.get("GROQ_API_KEY"), timeout=60.0, max_retries=5
        )
        # system_prompt lets a different persona reuse this same loop instead
        # of forking it.
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

    def chat(self, user_message: str, max_tool_rounds: int = 8) -> str:
        self.messages.append({"role": "user", "content": user_message})

        for _ in range(max_tool_rounds):
            response = self.client.chat.completions.create(
                model=MODEL,
                max_tokens=1500,
                messages=[{"role": "system", "content": self.system_prompt}, *self.messages],
                tools=GROQ_TOOL_SCHEMAS,
            )
            choice = response.choices[0]
            message = choice.message

            # Append the assistant turn exactly as returned (may carry tool_calls)
            self.messages.append(message.model_dump(exclude_none=True))

            if choice.finish_reason != "tool_calls":
                return message.content or ""

            # Execute every tool call in this turn and send results back
            for call in message.tool_calls:
                args = json.loads(call.function.arguments)
                print(f"  [tool] {call.function.name}({json.dumps(args)})")
                result = self._execute_tool(call.function.name, args)
                self.messages.append(
                    {"role": "tool", "tool_call_id": call.id, "content": result}
                )

        return "I hit the tool-call limit for one turn — try breaking the question down."

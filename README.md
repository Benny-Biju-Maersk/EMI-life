# FinBuddy — personal finance agent (Phase 1)

A single-agent, tool-using finance assistant for the Indian market. This is the
Phase-1 core that later grows into the multi-agent system (orchestrator +
credit / debt / markets / wealth / profile agents).

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # from console.anthropic.com
python main.py
```

Try:
- "What's the EMI on a 8 lakh car loan at 9.5% for 5 years?"
- "I earn 90k/month with 15k in EMIs. Can I afford a 1.2L phone on a 12-month EMI?"
- "What's Reliance trading at?" (needs internet; yfinance data is delayed)
- "I've paid 24 EMIs on a 30L home loan at 8.5% over 20 years. What does a 3L prepayment save me?"

## Layout

```
agent/agent.py        # the agent loop — read this first
tools/finance_tools.py# tool implementations (pure functions)
tools/schemas.py      # tool descriptions the model sees
tests/test_tools.py   # deterministic tests (pytest)
main.py               # CLI chat
```

## What to study in this code

1. `agent/agent.py` — the request → tool_use → tool_result → response loop.
   This loop is the whole idea of agentic development.
2. `tools/schemas.py` — tool descriptions are prompts. Change one and watch
   the model's tool-choice behavior change.
3. The system prompt — the compliance framing (education, not advice) lives
   here, not in code.

## Exercises (do these before adding features)

1. Break it on purpose: ask an affordability question without giving your
   income. Does the agent ask, or hallucinate numbers? Tighten the schema
   description until it reliably asks.
2. Add a `compare_loans` tool that takes two rate/tenure pairs and returns
   both EMI breakdowns.
3. Log every tool call to a JSONL file — your first observability layer.
4. Write 10 eval prompts with expected tool calls; script a checker.

## Product direction: checkout-EMI-trap MVP

A dedicated product-discovery session concluded FinBuddy's real wedge is
narrower and different from the roadmap below: intercept the moment someone
is about to take a "no-cost EMI" / BNPL offer at checkout, decode its true
cost, and give an unbiased gut-check — distributed as a WhatsApp bot. Full
writeup: [docs/product-brief.md](docs/product-brief.md). This **supersedes**
the Phase 3/4 roadmap items below where they conflict.

MVP: `whatsapp/webhook.py` (FastAPI + Twilio Sandbox), reusing
`agent/agent.py`'s loop with a different persona (`whatsapp/prompts.py`) and
a new `decode_emi_offer` tool (`tools/finance_tools.py`) rather than the
Phase 2 LangGraph split. See [CLAUDE.md](CLAUDE.md) for how to run it.

## Roadmap (superseded by the brief above where they conflict)

- Phase 2: orchestrator + specialists via LangGraph — see `agents/` and
  `chat.py`. Built (Credit/Debt + Markets specialists), left in place but
  unused — doesn't obviously serve the checkout-EMI-trap persona.
- Phase 3: FastAPI wrapper, SQLite user profiles, persistent context — now
  serves the checkout-EMI-trap wedge specifically (see the brief's "North
  Star" section), not a generic hosted web app.
- Phase 4: guardrail evals; monetized hosted product — the brief's
  savings-based subscription replaces the originally-scoped Stripe/auth
  web-app plan.
- Production data: AA gateway (Setu/Finvu), credit bureau API, Kite Connect
  replacing yfinance

## Disclaimers

Educational project. Outputs are financial information, not SEBI-registered
investment advice or a lending decision.

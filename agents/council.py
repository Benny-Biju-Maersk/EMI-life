"""The "LLM council": debate/consensus, a genuinely different pattern from
every other agent in this repo. Every specialist in agents/*.py is one
model reasoning + calling tools in a loop (ReAct) — this is instead
several *different* models answering the same question **independently**
(no model sees another's answer), followed by one more call where a
"chairman" model reads all of them and synthesizes — explicitly naming any
disagreement rather than picking a winner silently.

**Why this belongs in FinBuddy specifically, not just as a pattern to
learn:** the product's whole value proposition (see docs/decision.md's
moat argument) is being the one unbiased party in a checkout-EMI decision.
A single model's opinion on "should I take this loan" is still one
opinion, prone to that one model's particular blind spots — surfacing
where independent models actually disagree is itself informative for a
user trying to make an unbiased call, not just a novelty.

**When to reach for this vs. a single specialist:** genuinely high-stakes
or subjective questions ("should I take this loan", "is this a good
idea") where a single verdict papering over real uncertainty would be
worse than showing the uncertainty. NOT for anything with a deterministic
right answer (EMI math, a stock price) — that's wasteful 3x-4x the calls
for zero benefit; those stay on credit_debt_agent/markets_agent.

**Model choice — verified, not assumed:** Groq's lineup moves fast enough
that this repo has already been burned once by a hardcoded model name
going stale (see whatsapp/agent.py's note on qwen/qwen3.6-27b). These
three were confirmed live via `client.models.list()` on 2026-09-28 — the
account only has a handful of text-capable chat models at all right now,
so re-run that check before assuming these still exist:
- openai/gpt-oss-120b and openai/gpt-oss-20b — OpenAI's open-weight
  models, two different sizes (not just two prompts to the same weights).
- qwen/qwen3.8-27b — a different vendor (Alibaba) entirely, the real
  source of independence here.
No unbiased fourth model exists on this account to referee without also
being a panelist, so the chairman step reuses the largest panelist
(openai/gpt-oss-120b) — a documented simplification, not a hidden one.
"""

from __future__ import annotations

import asyncio
import json
import os

from dotenv import load_dotenv
from groq import AsyncGroq

from tools.knowledge import answer_from_knowledge_base

load_dotenv()

PANELIST_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
]
CHAIRMAN_MODEL = PANELIST_MODELS[0]

PANELIST_SYSTEM_PROMPT = """You are one independent panelist on FinBuddy's
advisory council, for a user in India. You do NOT see any other
panelist's answer — give your own honest, independent take.

Rules:
- You provide financial INFORMATION and EDUCATION, not personalized
  investment advice (not SEBI-registered) — never a buy/sell
  recommendation for a specific security.
- Currency is INR. Be concise (a few sentences) and concrete — a real
  verdict, not just "it depends," though naming real tradeoffs is fine.
- If the question is underspecified, state the assumption you're making
  rather than refusing to answer.
"""

CHAIRMAN_SYSTEM_PROMPT = """You are the chairman of FinBuddy's advisory
council. You've been given the SAME question answered independently by
several panelists, plus relevant facts from FinBuddy's own knowledge base.
Your job:
1. Synthesize one clear final answer.
2. Explicitly name any place the panelists actually disagreed — don't
   paper over it. Disagreement is useful information for the user, not a
   flaw to hide.
3. Ground your synthesis in the knowledge-base facts given, if any were
   relevant, and say so.
4. Same rules as the panelists: information/education only, never
   personalized investment advice, INR, concise and concrete.
"""


def _format_question(question: str, context: dict | None) -> str:
    if not context:
        return question
    return f"{question}\n\nKnown context about the user/situation:\n{json.dumps(context)}"


async def _ask_panelist(client: AsyncGroq, model: str, question: str, context: dict | None) -> dict:
    try:
        response = await client.chat.completions.create(
            model=model,
            max_tokens=600,
            messages=[
                {"role": "system", "content": PANELIST_SYSTEM_PROMPT},
                {"role": "user", "content": _format_question(question, context)},
            ],
        )
        return {"model": model, "answer": response.choices[0].message.content, "error": None}
    except Exception as e:
        # One panelist failing (rate limit, a retired model name) shouldn't
        # sink the whole council — the chairman synthesizes whoever did
        # answer, and the caller can see who didn't in "opinions".
        return {"model": model, "answer": None, "error": str(e)}


async def run_council(question: str, context: dict | None = None) -> dict:
    """Fan `question` out to every model in PANELIST_MODELS in parallel
    (each independent — no panelist sees another's answer), then have
    CHAIRMAN_MODEL synthesize a final answer grounded in whatever
    tools/knowledge.py has on the topic.

    `context`: optional extra facts to give every panelist and the
    chairman the same grounding (e.g. {"monthly_income": 90000,
    "existing_emis": 15000}) — plain dict, JSON-serialized into the prompt.

    Returns {"question", "opinions": [{"model","answer","error"}, ...],
    "synthesis"}, or {"error": ...} only if literally every panelist
    failed (e.g. GROQ_API_KEY missing/invalid) — a partial panel still
    produces a synthesis.
    """
    # timeout/max_retries above the SDK defaults: this machine's network
    # occasionally shows several-second cold-TLS-connection latency that
    # the default 2 retries don't ride out — see agents/orchestrator.py's
    # comment on the same tuning for ChatGroq.
    client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"), timeout=60.0, max_retries=5)
    opinions = await asyncio.gather(
        *(_ask_panelist(client, model, question, context) for model in PANELIST_MODELS)
    )
    usable = [o for o in opinions if o["answer"]]
    if not usable:
        return {"error": "every panelist failed to respond", "opinions": opinions}

    knowledge = answer_from_knowledge_base(question)
    knowledge_text = (
        "\n".join(f"- ({r['source']}) {r['text']}" for r in knowledge.get("results", []))
        or "(nothing directly relevant found)"
    )
    panel_text = "\n\n".join(f"Panelist ({o['model']}):\n{o['answer']}" for o in usable)

    chairman_response = await client.chat.completions.create(
        model=CHAIRMAN_MODEL,
        max_tokens=800,
        messages=[
            {"role": "system", "content": CHAIRMAN_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Question: {_format_question(question, context)}\n\n"
                    f"{panel_text}\n\n"
                    f"Relevant FinBuddy knowledge-base facts:\n{knowledge_text}"
                ),
            },
        ],
    )
    return {
        "question": question,
        "opinions": opinions,
        "synthesis": chairman_response.choices[0].message.content,
    }

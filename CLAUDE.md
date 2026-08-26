# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

FinBuddy — a personal finance assistant for the Indian market. **Current
product direction** (see [docs/product-brief.md](docs/product-brief.md),
which supersedes the README's original roadmap where they conflict):
intercept the moment someone is about to take a "no-cost EMI" / BNPL offer
at checkout, decode its true cost, and give an unbiased gut-check — a
WhatsApp bot, not a generic hosted web app. `whatsapp/` is that MVP; read
"Checkout-EMI-trap MVP" below first if you're picking this up fresh.

Three parallel implementations live in this repo, all runnable:

- **Phase 1** (`agent/`, `main.py`) — a single hand-rolled agent, one system
  prompt choosing among tools, built directly on the Anthropic Messages API
  with no framework. Intentionally minimal — read this first regardless of
  which direction you're working on; it's the loop every other
  implementation here is a variation of.
- **Checkout-EMI-trap MVP** (`whatsapp/`) — the current product direction.
  A FastAPI webhook for Twilio's WhatsApp Sandbox, running a LangGraph
  `create_react_agent` (`whatsapp/agent.py`) with a checkpointer for
  per-sender conversation memory — the one piece of Phase 2's work that
  turned out to be directly useful, though not the supervisor/multi-agent
  part of it (see "Checkout-EMI-trap MVP" below).
- **Phase 2** (`agents/`, `chat.py`) — a LangGraph multi-agent system built
  earlier, before the product-discovery session decided the direction above.
  Left in place, unused as a REPL — doesn't obviously serve the
  checkout-EMI-trap persona as a *supervisor+specialists* system (see the
  brief's "What likely doesn't survive"), though its `create_react_agent`
  pattern and `agents/tools.py` wrappers are what the WhatsApp MVP reuses.
  A supervisor routes to a Credit/Debt or Markets specialist agent. Same
  underlying tool math as Phase 1, reused not reimplemented.

Plus an **internal dashboard** (`dashboard/`) — a separate Next.js project,
read-only, no auth, for viewing WhatsApp conversations/tool-call logs. Not
part of the product; see "Internal dashboard" below.

## Setup & commands

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# .env (gitignored) holds ANTHROPIC_API_KEY, and optionally ANTHROPIC_BASE_URL /
# ANTHROPIC_MODEL if routing through a gateway like OpenRouter instead of
# api.anthropic.com directly — both agent/agent.py and agents/orchestrator.py
# read the same three vars, loaded via python-dotenv.
python main.py                          # Phase 1: single-agent REPL
python chat.py                          # Phase 2: multi-agent REPL (unused direction)
uvicorn whatsapp.webhook:app --reload   # Checkout-EMI-trap MVP: webhook server
cd dashboard && npm install && npm run dev   # Internal dashboard (needs data/finbuddy.db to exist)
```

Running the WhatsApp MVP end-to-end additionally needs `TWILIO_ACCOUNT_SID`
and `TWILIO_AUTH_TOKEN` in `.env` (from the Twilio console), plus a public
tunnel to your local server (e.g. `ngrok http 8000`) set as the Twilio
Sandbox's incoming-message webhook — see `whatsapp/webhook.py`'s docstring.

Tests:
```bash
python -m pytest tests/ -q                          # all tests
python -m pytest tests/test_tools.py::test_emi_known_value -q   # single test
```

`tests/test_tools.py` and `tests/test_whatsapp.py` are fully deterministic,
no API key or real Twilio account needed — the webhook test covers
signature validation and the no-input branch only, not a live agent reply
(that needs a real forwarded image; see `docs/product-brief.md`'s
verification steps to test that by hand).
`tests/test_agents.py` (Phase 2, unused direction) has one structural test
(no network) plus a live routing test that's skipped automatically when no
`ANTHROPIC_API_KEY` is set — when it does run, it makes real (billed) API
calls.
`yfinance` is optional/lazily imported (only `get_stock_quote` needs it).

## Architecture

The whole system is one request → tool_use → tool_result → response loop
(`agent/agent.py:FinanceAgent.chat`), talking to the Anthropic Messages API
directly (no framework). Read that file first — it's the entire agentic
pattern in ~80 lines:

1. `main.py` — terminal REPL; holds no logic, just wraps `FinanceAgent`.
2. `agent/agent.py` — owns the conversation loop and the system prompt.
   - `messages` is the full running transcript (list of dicts), mutated in
     place across turns — conversation state lives here, not in tool code.
   - Each `chat()` call loops up to `max_tool_rounds` (default 8): call the
     model, and if `stop_reason == "tool_use"`, execute every requested tool
     call, append a `tool_result` block per call in one `user` message, and
     loop again. Returns plain text once the model stops requesting tools.
   - Tool execution never raises into the loop: exceptions are caught and
     serialized as `{"error": ...}` JSON sent back to the model as a tool
     result, so the model can recover or explain rather than crashing.
   - The system prompt is where the compliance framing lives (education not
     advice, must ask for income before affordability checks, INR default) —
     not enforced in code, so changing tool behavior via the prompt is
     expected and normal here.
3. `tools/finance_tools.py` — plain, deterministic, side-effect-free
   functions (except `get_stock_quote`, which hits the network via
   `yfinance` and lazily imports it). `TOOL_FUNCTIONS` is the name→function
   registry the agent dispatches through; adding a tool means adding it here
   AND to `TOOL_SCHEMAS` in schemas.py — the two are matched by name and
   kept in sync manually, nothing validates that at runtime.
4. `tools/schemas.py` — Anthropic tool-use JSON schemas. Treat the
   `description` fields as prompts, not documentation — they're what the
   model reads to decide *when* to call a tool and what to ask the user for
   first (e.g. `affordability_check`'s description is what makes the model
   ask for income instead of guessing it).
5. `tests/test_tools.py` — tests hit `tools/finance_tools.py` functions
   directly with known values; no agent/API mocking exists in this repo.

### Checkout-EMI-trap MVP (`whatsapp/`) — current product direction

Runs on `whatsapp/agent.py`'s LangGraph agent, not `agent/agent.py`'s
hand-rolled loop — the one part of Phase 2's work actually reused, and
deliberately just the single-agent `create_react_agent` piece, not the
supervisor/multi-agent split (a WhatsApp bot with 3 tools doing one job
doesn't need routing between specialists).

1. `whatsapp/prompts.py` — `CHECKOUT_SYSTEM_PROMPT`, scoped to decoding a
   forwarded checkout-offer screenshot: extract terms from the image, ask
   (don't guess) for anything relevant the image doesn't show, call
   `decode_emi_offer` for the real numbers, fold in `affordability_check` if
   income/EMIs are known.
2. `whatsapp/agent.py` — `build_whatsapp_agent()`: a
   `langgraph.prebuilt.create_react_agent` carrying `CHECKOUT_TOOLS`
   (`agents/tools.py`) and `CHECKOUT_SYSTEM_PROMPT`, with a
   `langgraph.checkpoint.sqlite.SqliteSaver` checkpointer. **This is the
   actual reason to prefer LangGraph over `agent/agent.py` here**: the
   checkpointer remembers a conversation by `thread_id` across separate
   `.invoke()` calls — i.e. across separate WhatsApp messages — with no
   hand-rolled session dict, and (since the `SqliteSaver` swap) across
   process restarts too. Backed by `data/finbuddy.db` — the same file
   `whatsapp/storage.py` logs to, different tables (LangGraph manages its
   own `checkpoints`/`writes` schema). Build this graph **once per
   process** (`webhook.py` does it at import time) — rebuilding per-request
   opens a fresh sqlite3 connection for no reason.
3. `whatsapp/webhook.py` — the FastAPI app. One route, `POST /whatsapp`:
   validates the request is genuinely from Twilio
   (`twilio.request_validator.RequestValidator` + `TWILIO_AUTH_TOKEN` — a
   public webhook otherwise lets anyone burn API credits), builds either a
   multimodal content list (image block fetched from Twilio's protected
   `MediaUrl0` + a text block) or plain text, then calls
   `GRAPH.invoke({"messages": [...]}, config={"configurable": {"thread_id":
   from_number}})` — the sender's WhatsApp number **is** the `thread_id`
   that ties their messages together in the checkpointer. After each
   invoke, diffs `result["messages"]` against the pre-invoke message count
   (from `GRAPH.get_state(config)`) and passes just the new ones to
   `storage.log_turn(...)` — never string-matching, never re-logging
   history.
   - Every branch (no input, bad signature, a tool/API error mid-invoke)
     still returns a valid TwiML reply rather than a bare 500 — a WhatsApp
     user with no response looks identical to a crash from their side.
   - Storage logging is wrapped in its own `try/except` — a logging failure
     must never turn a successful reply into a failed one.
4. `whatsapp/storage.py` — plain `sqlite3` (stdlib, no ORM), two tables in
   `data/finbuddy.db`: `messages` (one row per user/assistant turn) and
   `tool_calls` (one row per tool call, structured — this is what makes
   "decoded offers" a queryable list rather than text buried in a
   transcript). `log_turn()` walks a list of new LangChain message objects,
   matching each `AIMessage.tool_calls` entry to the `ToolMessage` that
   follows it by `tool_call_id`. This is what `dashboard/` reads — see
   below.
5. `tools/finance_tools.py:decode_emi_offer` — the one genuinely new tool
   this direction needed: computes the hidden cost a "no-cost EMI" claim
   doesn't show (processing fee + GST on it, a discount only available on
   full payment), reusing `calculate_emi` rather than duplicating its
   amortization math when the offer does state real interest. Wrapped for
   LangChain as `decode_emi_offer_tool` in `agents/tools.py`, and also
   registered in `tools/schemas.py`/`TOOL_FUNCTIONS` so Phase 1's
   `main.py` REPL can use it directly too.

### Internal dashboard (`dashboard/`)

A separate Next.js (App Router, TypeScript, Tailwind, shadcn) project — its
own `package.json`/`node_modules`, independent of the repo-root
`package.json` (that one's just for the shadcn MCP server's own `npx`
invocation, see `.mcp.json`). Read-only, no auth, no API layer: this is a
local tool for one person, not part of the product.

- `src/lib/db.ts` — `better-sqlite3` opens `../data/finbuddy.db` directly
  (`server-only`-guarded, read-only connection). No FastAPI endpoints exist
  for this — the dashboard and the WhatsApp bot are coupled by sharing a
  filesystem path, which is fine for "runs on your machine, for you" and
  would need revisiting only if the two ever need to run on different
  hosts. `next.config.ts` sets `serverExternalPackages: ["better-sqlite3"]`
  since it has a native binding Turbopack shouldn't try to bundle.
- `src/app/page.tsx` — thread list (`listThreads()`): WhatsApp number,
  message count, last activity.
- `src/app/conversations/[threadId]/page.tsx` — one thread's full timeline,
  messages and tool calls merged and sorted by timestamp. `params` is a
  `Promise` (Next.js 16 — no synchronous access exists anymore); a
  tool call's `verdict` field (when its JSON output has one, e.g.
  `decode_emi_offer`) gets pulled out into a `Badge` rather than left
  buried in the raw JSON dump.

Run it: `cd dashboard && npm install && npm run dev` (needs
`data/finbuddy.db` to already exist — run the WhatsApp bot, or the
Python smoke-test pattern in `docs/decision.md`, at least once first).

### Phase 2 — multi-agent orchestrator (`agents/`, `chat.py`, unused direction)

Same core idea as Phase 1 — a model deciding when to call tools — but with
an extra layer: a **supervisor** LLM decides which **specialist agent**
handles a message, and each specialist runs its own tool-calling loop.

1. `agents/orchestrator.py` — `build_graph()` builds two specialists, wires
   them into a supervisor graph via `langgraph_supervisor.create_supervisor`,
   and returns the compiled graph. Read this first for Phase 2, same role
   `agent/agent.py` plays for Phase 1.
   - The supervisor is itself an LLM call with two tools it can pick from —
     `transfer_to_credit_debt_agent` / `transfer_to_markets_agent` — added
     automatically by `create_supervisor`. Handoff isn't hand-rolled routing
     logic; it's the same "model picks a tool" pattern as everything else
     here, just with "the tool" being "another agent."
   - `MODEL` here mirrors `agent/agent.py`'s pattern (env var with a
     hardcoded fallback) — keep the two in sync if you change the default.
2. `agents/credit_debt_agent.py`, `agents/markets_agent.py` — each is a
   `langgraph.prebuilt.create_react_agent(...)` with its own scoped system
   prompt and its own tool subset. Adding a third specialist means adding a
   third file matching this pattern and registering it in
   `orchestrator.py`'s `agents=[...]` list.
   - `create_react_agent` is currently deprecated in favor of
     `langchain.agents.create_agent` (LangGraph v1.0, removed in v2.0) —
     `langgraph_supervisor` itself hasn't migrated yet either, so this is a
     library-wide pending change, not something to silently "fix" here
     without checking `langgraph_supervisor`'s own migration first.
3. `agents/tools.py` — LangChain `@tool`-wrapped versions of
   `tools/finance_tools.py`'s functions. **No math lives here** — every
   wrapper calls straight into the Phase-1 function and `json.dumps`s the
   result. Add a tool's logic to `tools/finance_tools.py` first (and its
   Phase-1 schema in `tools/schemas.py` if Phase 1 should also get it), then
   wrap it here and assign it to a specialist's tool list.
4. `chat.py` — Phase 2's REPL. Unlike `main.py`'s single `messages` list,
   this drives `graph.stream(...)` and prints each node's handoffs/tool
   calls as they happen (`_print_trace`) — the multi-agent equivalent of
   Phase 1's `[tool] name(...)` line, since routing is otherwise invisible.

Optional tracing: set `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` (a
free LangSmith account) to get every handoff and tool call visualized in
LangSmith's UI instead of relying on `chat.py`'s printed trace — not
required to run the system.

## Conventions specific to this repo

- Tools return plain dicts (JSON-serialized by the agent loop), including on
  error — `{"error": "..."}` rather than raising, both inside tool functions
  and in `_execute_tool`'s wrapper. Keep new tools consistent with this.
- Currency is INR and unstated rates/tenures follow Indian lending norms
  (e.g. FOIR thresholds in `affordability_check`, default 15% rate for
  consumer loans) — these are domain defaults, not arbitrary.
- `MODEL` is pinned as a module constant in `agent/agent.py` (Phase 1),
  `agents/orchestrator.py` (Phase 2), and `whatsapp/agent.py` (checkout MVP)
  — all three read `ANTHROPIC_MODEL` with the same hardcoded fallback;
  update all three if you change the default.
- `langchain-anthropic` pins `anthropic<1.0.0`, so installing
  `requirements.txt` keeps the raw SDK on 0.125.x even though `pip install
  anthropic` alone would give you 1.0.0 — both Phase 1 and Phase 2 have been
  verified to work against the pinned 0.125.x.

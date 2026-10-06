# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

FinBuddy — a personal finance assistant for the Indian market. **Current
product direction** (see [docs/product-brief.md](docs/product-brief.md) and
`docs/decision.md` #16, which supersede the README's original roadmap where
they conflict): decode the true cost of a "no-cost EMI"/BNPL offer at
checkout and give an unbiased gut-check, growing into a broader "single
portal for your money" — a personalized, multi-agent, multi-widget web
dashboard is now the **primary** product surface, with the WhatsApp bot
that originally shipped this (still fully working) as a secondary/backend
channel rather than the front door. Read "Public web portal" below first if
you're picking this up fresh; read "Checkout-EMI-trap MVP" for the
WhatsApp-specific piece.

Four parallel implementations live in this repo, all runnable:

- **Phase 1** (`agent/`, `main.py`) — a single hand-rolled agent, one system
  prompt choosing among tools, built directly on Groq's OpenAI-compatible
  Chat Completions API (via the `groq` SDK) with no framework. Intentionally
  minimal — read this first regardless of which direction you're working
  on; it's the loop every other implementation here is a variation of.
- **Public web portal** (`web/`, `api/`) — the current primary product
  surface. A Next.js app (Clerk auth) presenting FinBuddy's capabilities as
  a signed-in dashboard of widgets, backed by a FastAPI service
  (`api/main.py`) that's the only thing importing `tools/*.py` on this
  surface. See "Public web portal" below.
- **Checkout-EMI-trap MVP** (`whatsapp/`) — the original MVP, now
  secondary/backend channel. A FastAPI webhook for Twilio's WhatsApp
  Sandbox, running a LangGraph `create_react_agent` (`whatsapp/agent.py`)
  with a checkpointer for per-sender conversation memory — the one piece of
  Phase 2's work that turned out to be directly useful, though not the
  supervisor/multi-agent part of it (see "Checkout-EMI-trap MVP" below).
- **Phase 2** (`agents/`, `chat.py`) — a LangGraph multi-agent supervisor,
  now the engine behind the web portal's chat/council widgets (not just an
  unused REPL anymore — see "Public web portal" and "Phase 2" below). A
  supervisor routes to one of six specialists (credit/debt, markets,
  budget, research, reminders, or a multi-model "council" for high-stakes
  judgment calls). Same underlying tool math as Phase 1, reused not
  reimplemented.

Plus an **internal dashboard** (`dashboard/`) — a separate Next.js project,
read-only, no auth, for viewing WhatsApp conversations/tool-call logs. Not
part of the product; see "Internal dashboard" below.

## Setup & commands

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# .env (gitignored) holds GROQ_API_KEY and optionally GROQ_MODEL (default
# openai/gpt-oss-120b) — agent/agent.py and agents/orchestrator.py read
# both, loaded via python-dotenv. whatsapp/agent.py reads GROQ_VISION_MODEL
# instead (default a Qwen3 checkpoint), since it has to read a forwarded
# checkout screenshot and GROQ_MODEL's text-only model can't see images at
# all. Groq's model lineup moves fast — reverify with the account's own
# `client.models.list()` before assuming either default name still exists.
python main.py                          # Phase 1: single-agent REPL
python chat.py                          # Phase 2: multi-agent REPL (now includes the council)
uvicorn whatsapp.webhook:app --reload   # Checkout-EMI-trap MVP: webhook server
uvicorn api.main:app --reload --port 8001   # Public web portal: FastAPI backend
cd web && npm install && npm run dev         # Public web portal: Next.js frontend (localhost:3000)
cd dashboard && npm install && npm run dev   # Internal dashboard (needs data/finbuddy.db to exist)
```

Running the WhatsApp MVP end-to-end additionally needs `TWILIO_ACCOUNT_SID`
and `TWILIO_AUTH_TOKEN` in `.env` (from the Twilio console), plus a public
tunnel to your local server (e.g. `ngrok http 8000`) set as the Twilio
Sandbox's incoming-message webhook — see `whatsapp/webhook.py`'s docstring.

Running `web/` needs a real Clerk secret key in `web/.env.local`
(`CLERK_SECRET_KEY`, from dashboard.clerk.com → API Keys) — with only the
placeholder in `.env.local.example`, `ClerkProvider` wrapping the root
layout makes *every* page 500, not just sign-in.

The two MCP servers `agents/mcp_tools.py` loads (`mcp-server-fetch`,
`free-search-mcp`) run via `uvx`, not `pip install` — the machine needs
`uv` on it (installed via `requirements.txt`'s `uv` entry, but `uvx` lands
in the current user's site Scripts dir, which `agents/mcp_tools.py`
resolves itself via `sysconfig` rather than assuming it's on PATH).

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
`tests/test_agents.py` (Phase 2, now the web portal's engine) has one
structural test (no network) plus a live routing test that's skipped
automatically when no `GROQ_API_KEY` is set — when it does run, it makes
real (billed) API calls. `tests/test_council.py` follows the same
structural/live split for `agents/council.py`. `tests/test_knowledge.py`
(RAG retrieval) is fully deterministic, no API key needed.
`yfinance` is optional/lazily imported (only `get_stock_quote` needs it).

## Architecture

The whole system is one request → tool_use → tool_result → response loop
(`agent/agent.py:FinanceAgent.chat`), talking to Groq's OpenAI-compatible
Chat Completions API directly via the `groq` SDK (no framework). Read that
file first — it's the entire agentic pattern in ~80 lines:

1. `main.py` — terminal REPL; holds no logic, just wraps `FinanceAgent`.
2. `agent/agent.py` — owns the conversation loop and the system prompt.
   - `messages` is the full running transcript (list of dicts), mutated in
     place across turns — conversation state lives here, not in tool code.
   - Each `chat()` call loops up to `max_tool_rounds` (default 8): call the
     model, and if `finish_reason == "tool_calls"`, execute every requested
     tool call and append one `role: "tool"` message per call. Returns plain
     text once the model stops requesting tools.
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
4. `tools/schemas.py` — Anthropic-shaped tool-use JSON schemas
   (`TOOL_SCHEMAS`), plus `GROQ_TOOL_SCHEMAS` — the same schemas reshaped
   into OpenAI-style function-calling format at import time, since `groq`
   (Phase 1's actual runtime now) speaks that shape instead. Treat the
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

### Phase 2 — multi-agent orchestrator (`agents/`, `chat.py`)

Same core idea as Phase 1 — a model deciding when to call tools — but with
an extra layer: a **supervisor** LLM decides which **specialist agent**
handles a message, and each specialist runs its own tool-calling loop. No
longer just a REPL exercise — this is the graph `agents/web_graph.py` wraps
with persistent memory for the public web portal (see below), and
`chat.py` is still the fastest way to exercise routing changes by hand.

1. `agents/orchestrator.py` — `build_graph()` builds every specialist,
   wires them into a supervisor graph via
   `langgraph_supervisor.create_supervisor`, and returns the compiled
   graph. Read this first for Phase 2, same role `agent/agent.py` plays
   for Phase 1. **Must be invoked async** (`await graph.ainvoke(...)` /
   `graph.astream(...)`, never the sync forms) — research_agent carries
   MCP tools and council_agent's tool runs several models in parallel via
   `asyncio.gather`, both async-only.
   - The supervisor is itself an LLM call with a `transfer_to_<agent>` tool
     per specialist, added automatically by `create_supervisor`. Handoff
     isn't hand-rolled routing logic; it's the same "model picks a tool"
     pattern as everything else here, just with "the tool" being "another
     agent."
   - Six specialists as of this writing: `credit_debt_agent`,
     `markets_agent`, `budget_agent`, `research_agent`, `reminder_agent`,
     `council_agent`. Adding a seventh means a new file matching the
     `create_react_agent(...)` pattern, registered in `agents=[...]` here.
   - `MODEL` here mirrors `agent/agent.py`'s pattern (env var with a
     hardcoded fallback) — keep the two in sync if you change the default.
   - `create_react_agent` is currently deprecated in favor of
     `langchain.agents.create_agent` (LangGraph v1.0, removed in v2.0) —
     `langgraph_supervisor` itself hasn't migrated yet either, so this is a
     library-wide pending change, not something to silently "fix" here
     without checking `langgraph_supervisor`'s own migration first.
2. `agents/tools.py` — LangChain `@tool`-wrapped versions of
   `tools/finance_tools.py`'s (and other `tools/*.py`) functions. **No
   math lives here** — every wrapper calls straight into the underlying
   function and `json.dumps`s the result. Add a tool's logic to its
   `tools/*.py` module first, then wrap it here and assign it to a
   specialist's tool list.
3. `chat.py` — Phase 2's REPL, async top-to-bottom (`asyncio.run(main())`,
   `graph.astream(...)`) for the reason above. Unlike `main.py`'s single
   `messages` list, this prints each node's handoffs/tool calls as they
   happen (`_print_trace`) — the multi-agent equivalent of Phase 1's
   `[tool] name(...)` line, since routing is otherwise invisible.

Optional tracing: set `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` (a
free LangSmith account) to get every handoff and tool call visualized in
LangSmith's UI instead of relying on `chat.py`'s printed trace — not
required to run the system.

### Multi-agent council, MCP tools, and RAG

Three additions layered onto Phase 2, each a genuinely different pattern
from plain ReAct tool-calling — added together as a hands-on multi-agent
learning track, and because the product's "unbiased gut-check" positioning
(see `docs/decision.md`'s moat argument) makes surfacing model disagreement
a real feature, not just a novelty.

1. **The council** (`agents/council.py`, `agents/council_agent.py`) —
   debate/consensus: `run_council(question, context)` fans a question out
   to several Groq models **in parallel, independently** (no panelist sees
   another's answer), then a "chairman" call synthesizes, explicitly
   naming any disagreement rather than hiding it. `PANELIST_MODELS` is a
   hardcoded list *verified live* against this account's actual
   `client.models.list()` — Groq's lineup moves fast (see Setup &
   commands), don't assume it still matches without re-checking.
   `agents/council_agent.py` wraps it as a normal specialist (one tool,
   `consult_council_tool`) so it slots into `orchestrator.py`'s
   `agents=[...]` like everything else. Use for genuinely high-stakes/
   subjective questions only — routine EMI math stays on
   `credit_debt_agent`, running 3-4x the model calls for a deterministic
   answer is pure waste.
2. **MCP tools** (`agents/mcp_tools.py`) — `research_agent` is the only
   specialist wired to external MCP servers (others already do their whole
   job with local DB reads/pure math — see that file's docstring for why
   not everywhere): `mcp-server-fetch` (official Anthropic reference
   server, reads a URL's full text) and `free-search-mcp` (no-API-key
   multi-engine web search). Both run as isolated `uvx <package>`
   subprocesses, never `pip install`ed into this repo's venv — doing that
   once already pulled a newer `mcp` SDK/`starlette` combo that broke
   `fastapi` (see `requirements.txt`'s `fastapi>=0.140` comment). Async-only
   — see Phase 2's invocation note above.
3. **RAG** (`tools/knowledge.py`, `knowledge/*.md`) — a handful of
   FinBuddy-curated facts (FOIR rules, what "no-cost EMI" hides, credit
   score factors, the SEBI-RIA line) retrieved via TF-IDF + cosine
   similarity (`scikit-learn`), not a real embedding model — deliberately
   simple, no model download, easy to read start to finish. Wrapped as
   `answer_from_knowledge_base_tool` for `research_agent` and read directly
   by the council's chairman step for grounding.

### Public web portal (`web/`, `api/`)

The current primary product surface (see "What this is" above) — a
personalized, multi-widget dashboard, not a chat window. Two apps:

1. **`api/main.py`** — FastAPI, imports `tools/*.py` directly (same
   "logic lives once" convention as every other surface). **Two trust
   levels**, spelled out in its module docstring:
   - *Public* (`/decode-offer`, `/calculate-emi`, `/prepayment-impact`,
     `/stock-quote`, `/market-news`): stateless, no user identity, safe
     for a browser to call directly — same reasoning as the WhatsApp bot
     needing no account for the checkout-interception moment.
   - *Internal* (`/profile`, `/profile/loans`, `/profile/expenses`,
     `/budget-snapshot`, `/personalized-updates`, `/reminders`, `/chat`,
     `/council`): read/write one specific user's data. **This API does
     not verify Clerk sessions itself** — `web/`'s own Next.js
     server-side route handlers (`app/api/*/route.ts`) call `auth()`
     (already verified server-side) and only then call these endpoints,
     passing the verified `user_id` themselves. The browser never talks
     to these directly. Known simplification, not glossed over: on
     localhost this boundary is enforced by nothing but "the browser
     doesn't know this port exists for these routes" — fine for local
     dev, needs a shared secret or real JWT verification before deploying
     anywhere reachable by someone else.
   - `/chat` and `/council` are the two agentic endpoints, both `async
     def` (unlike every sync endpoint above) — they call
     `agents/web_graph.py`/`agents/council.py`, both async-only. The
     compiled graph is built once at process startup via a FastAPI
     `lifespan` context manager (async-native), not bare import-time code
     the way `whatsapp/webhook.py`'s `GRAPH = build_whatsapp_agent()` is —
     `agents/web_graph.py`'s builder is itself `async def` and can't wrap
     its own MCP tool loading in `asyncio.run()` from inside uvicorn's
     already-running event loop.
2. **`agents/web_graph.py`** — the full Phase 2 supervisor graph (every
   specialist, the council, MCP tools) wired to `AsyncSqliteSaver`
   (`langgraph.checkpoint.sqlite.aio` — **not** `whatsapp/agent.py`'s
   plain `SqliteSaver`, which only supports sync checkpoint methods and
   raises under `.ainvoke()`), keyed by Clerk user id as the LangGraph
   `thread_id` instead of a WhatsApp number. Same "build once per
   process" reasoning as `whatsapp/agent.py`.
3. **`web/`** — Next.js (App Router, TypeScript, Tailwind, Clerk auth),
   seeded from `dashboard/`'s stack but a separate app/security posture
   (see `docs/decision.md` #16 for why not just extending `dashboard/`).
   - `app/dashboard/page.tsx` — the signed-in widget grid (redirects to
     `/sign-in` if signed out, to `/onboarding` if no income saved yet).
     Each widget in `app/dashboard/_components/` is a client component
     calling this app's own `/api/*` route, never `api/main.py` directly.
   - `app/api/*/route.ts` — one per widget, each: verify `auth()`, 401 if
     signed out, forward to `api/main.py` with the verified `user_id`
     injected. This is the actual trust boundary — see api/main.py's note
     above.
   - `app/decode/page.tsx` — the original standalone decode form, calling
     the *public* `/decode-offer` endpoint directly, no auth — kept
     alongside the dashboard's own decode widget since decoding an offer
     was always meant to not require an account.
   - Needs a real `CLERK_SECRET_KEY` in `web/.env.local` (see Setup &
     commands) — Next.js 16 renamed the `middleware.ts` convention to
     `proxy.ts` and `@clerk/nextjs` 7.x ("Core 3") removed
     `<SignedIn>`/`<SignedOut>` in favor of `auth()` from
     `@clerk/nextjs/server`, both hit while building this; `web/AGENTS.md`
     flags the same "don't trust remembered Next.js APIs" warning.

## Conventions specific to this repo

- Tools return plain dicts (JSON-serialized by the agent loop), including on
  error — `{"error": "..."}` rather than raising, both inside tool functions
  and in `_execute_tool`'s wrapper. Keep new tools consistent with this.
- Currency is INR and unstated rates/tenures follow Indian lending norms
  (e.g. FOIR thresholds in `affordability_check`, default 15% rate for
  consumer loans) — these are domain defaults, not arbitrary.
- `MODEL` is pinned as a module constant in `agent/agent.py` (Phase 1) and
  `agents/orchestrator.py` (Phase 2) — both read `GROQ_MODEL` with the same
  hardcoded fallback (`openai/gpt-oss-120b`); update both if you change
  the default. `whatsapp/agent.py` (checkout MVP) is the one deliberate
  exception: it reads `GROQ_VISION_MODEL` instead, since decoding a
  forwarded screenshot needs a vision-capable model and `GROQ_MODEL`'s fast
  text models can't see images.
- All three implementations run on Groq (via the `groq` SDK in Phase 1,
  `langchain-groq`'s `ChatGroq` in Phase 2 and the WhatsApp MVP) — not
  Anthropic/Claude. `tools/schemas.py`'s `TOOL_SCHEMAS` stay Anthropic-shaped
  (name/description/input_schema) since that's still valid JSON Schema;
  `GROQ_TOOL_SCHEMAS` in the same file is a mechanical reshape of it for
  Phase 1's OpenAI-style tool calls. LangChain's `ChatGroq` handles the
  reshape itself for Phase 2/the WhatsApp MVP, since those tools are
  LangChain `@tool`-wrapped, not read from `tools/schemas.py`.

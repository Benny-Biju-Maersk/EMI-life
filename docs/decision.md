# FinBuddy — Technical Decisions

Why the code looks the way it does. Product decisions (the wedge,
distribution, monetization, the SEBI line) live in
[product-brief.md](product-brief.md) — this file is about *implementation*
choices only, across all three runnable pieces: Phase 1 (`agent/`), Phase 2
(`agents/`, unused direction), and the current product,
the WhatsApp MVP (`whatsapp/`).

Each entry: the problem, the decision, why, and what it costs.

---

## 1. Phase 1 talks to the raw Anthropic Messages API, no framework

**Decision:** `agent/agent.py` calls `anthropic.Anthropic().messages.create()`
directly — no LangChain, no LangGraph.

**Why:** the entire "agent" idea is one loop: send a transcript + tool
schemas, get back text or tool-call requests, execute, feed results back,
repeat. Writing it by hand (~80 lines, [agent/agent.py](../agent/agent.py))
makes that loop impossible to hide behind a framework abstraction — read it
once and every other agent framework's internals stop being mysterious.

**Cost:** no free multi-agent routing, no built-in tracing — Phase 2 exists
specifically to show what a framework buys you on top of this.

---

## 2. Tools are plain functions; schemas are a hand-kept parallel list

**Decision:** `tools/finance_tools.py` holds pure functions and a
`TOOL_FUNCTIONS` name→function dict. `tools/schemas.py` holds the matching
Anthropic JSON schemas in `TOOL_SCHEMAS`. Nothing validates at runtime that
the two lists agree.

**Why:** keeps tool logic and tool *description* (what the model reads to
decide when/how to call it) physically separate, which makes the schema's
role as a prompt more visible — you can edit a `description` string and
watch tool-choice behavior change without touching any logic.

**Cost:** add a tool to one file and forget the other, and you get a
silent mismatch, not an error, until the model tries to call something
that isn't registered. There is no test enforcing the two stay in sync.

---

## 3. Tool errors are returned as JSON data, never raised into the loop

**Decision:** `FinanceAgent._execute_tool` catches every exception and
returns `json.dumps({"error": str(e)})` as the tool result, instead of
letting it propagate.

**Why:** an agent loop's job is to keep going. A tool exception is just
more information the model can react to ("that didn't work, let me ask a
follow-up" or "let me explain why") rather than a reason to crash the whole
turn.

**Cost:** a genuine bug inside a tool function looks identical to the model
as a bad user input — it will try to "recover" from real bugs too, which
can mask them during development. Worth grepping for this pattern in tests
if a tool's exceptions look suspiciously well-handled.

---

## 4. Compliance and behavior framing lives in the system prompt, not code

**Decision:** things like "ask for income before an affordability check,"
"never recommend a specific stock," "INR by default" are English sentences
in `SYSTEM_PROMPT` ([agent/agent.py](../agent/agent.py)) and
`CHECKOUT_SYSTEM_PROMPT` ([whatsapp/prompts.py](../whatsapp/prompts.py)),
not `if` statements.

**Why:** this is genuinely how tool-calling LLM agents are steered — the
prompt *is* the interface for behavior a schema can't express (schemas
describe tool shape, not conversational policy). Changing behavior here is
expected, not a hack.

**Cost:** nothing here is guaranteed. A rule like "ask before calling
`affordability_check`" is a strong suggestion the model usually follows,
not an invariant — see `learnings.md`'s note on testing this by hand.

---

## 5. Phase 2 is a second, parallel implementation — not a replacement

**Decision:** `agents/orchestrator.py` builds a
`langgraph_supervisor.create_supervisor` graph routing to two
`langgraph.prebuilt.create_react_agent` specialists
([credit_debt_agent.py](../agents/credit_debt_agent.py),
[markets_agent.py](../agents/markets_agent.py)). It runs the *same*
underlying tool math as Phase 1, just through a framework and a routing
layer.

**Why:** built as the "orchestrator + specialists" step in the original
roadmap, deliberately kept side-by-side with Phase 1 rather than replacing
it, so both patterns (hand-rolled loop vs. framework-provided ReAct loop +
supervisor handoff) stay comparable in one repo.

**Cost:** `create_react_agent` is deprecated in favor of
`langchain.agents.create_agent` (removed in LangGraph v2.0);
`langgraph_supervisor` hasn't migrated either, so this is a pending
library-wide change, not something to "fix" here in isolation.

**Now:** superseded as the product direction (see `product-brief.md`) —
left in place, unused, not yet formally retired. `agents/tools.py`'s
`@tool`-wrapped functions still just call straight into
`tools/finance_tools.py`, so Phase 1 changes (like `decode_emi_offer`)
don't silently desync Phase 2's math even though Phase 2 doesn't use that
tool yet.

---

## 6. The WhatsApp MVP runs on a LangGraph agent, not `agent/agent.py`'s loop

**Decision:** `whatsapp/agent.py`'s `build_whatsapp_agent()` builds a
`langgraph.prebuilt.create_react_agent` — the same single-agent pattern
already proven in Phase 2's `agents/credit_debt_agent.py` — carrying
`CHECKOUT_TOOLS` (`agents/tools.py`) and `CHECKOUT_SYSTEM_PROMPT`
(`whatsapp/prompts.py`). `whatsapp/webhook.py` calls `GRAPH.invoke(...)`,
not `FinanceAgent.chat(...)`.

**Why (superseded from an earlier version of this decision):** originally
built by reusing `agent/agent.py`'s loop verbatim, on the reasoning that the
loop doesn't care how a message arrives. That held right up until per-user
*memory* became a real requirement — at which point LangGraph's
checkpointer (see decision 8) was worth the framework dependency this
specific channel didn't otherwise need. Not the supervisor/multi-agent
split from `agents/orchestrator.py` — a WhatsApp bot doing one job with 3
tools doesn't need routing between specialists, just the single
`create_react_agent` piece.

**Enabler still in place, just unused by this path:**
`FinanceAgent.__init__`'s `system_prompt` parameter (added for this
decision's original version) remains — `main.py`'s Phase-1 REPL still uses
it with its default persona, `agent/agent.py`'s loop is otherwise
untouched.

---

## 7. `FinanceAgent.chat` accepts `str` or `list[dict]` content — built for multimodal without touching the loop

**Decision:** `chat()`'s `user_message` type is `str | list[dict]`, appended
to `self.messages` as-is either way.

**Why:** a forwarded WhatsApp screenshot needs an image content block plus
a text block in one user turn — the Anthropic API already accepts either
shape for a message's `content`. Rather than adding an `image` parameter or
a separate code path, the loop just passes whatever it's given straight
through. `whatsapp/webhook.py` builds `[{"type": "image", ...},
{"type": "text", ...}]` and hands it to the *same* `chat()` a REPL string
goes through.

**Lesson embedded here:** a primitive built generically at Phase 1 (opaque
content, not "a string") meant the multimodal WhatsApp use case needed zero
changes to the core loop when it showed up later.

---

## 8. Per-sender memory via a LangGraph checkpointer keyed by `thread_id`, in-memory only

**Decision:** `whatsapp/agent.py` attaches a
`langgraph.checkpoint.memory.MemorySaver()` to the agent graph.
`whatsapp/webhook.py` passes Twilio's `From` field as the LangGraph
`thread_id` (`config={"configurable": {"thread_id": from_number}}`) on
every `GRAPH.invoke(...)` call. No hand-rolled session dict, no database.

**Why (supersedes an earlier hand-rolled version of this decision):** this
used to be a plain `SESSIONS: dict[str, FinanceAgent]` in `webhook.py`
itself. Swapping to a checkpointer does the same job — one sender's
messages don't bleed into another's — but for free as part of adopting
LangGraph for this path (decision 6), and with a real advantage: swapping
`MemorySaver` for a persistent checkpointer (e.g. `langgraph-checkpoint-
sqlite`'s `SqliteSaver`) later is a one-line change in
`build_whatsapp_agent()`, not a rewrite of how sessions are tracked. A full
user-profile store (income/EMI history, not just message history) is still
explicitly deferred — see `product-brief.md`'s "North Star" section —
because validating the wedge doesn't need it yet.

**Cost:** `MemorySaver` is still in-memory-only — restart the server, every
conversation resets, same as the hand-rolled version it replaced. That gap
is now purely a checkpointer-backend choice, not an architecture change,
which is the whole point of this decision.

---

## 9. Twilio webhook signature validation is a first-class gate, with a visible dev-mode bypass

**Decision:** every `POST /whatsapp` is validated with
`twilio.request_validator.RequestValidator` against `TWILIO_AUTH_TOKEN`
before anything else happens — *unless* `TWILIO_AUTH_TOKEN` isn't set, in
which case validation is skipped with an inline comment: `# don't deploy
like this`.

**Why:** a public webhook with no validation lets anyone who finds the URL
POST fake messages and burn Anthropic API credits on your bill. The bypass
exists purely so local development works before Twilio credentials are
configured — it's a convenience with a loud comment attached, not a
default anyone should ship.

**Also:** `_request_url()` reconstructs the externally-visible URL from
`X-Forwarded-Proto`/`X-Forwarded-Host` headers, because a local tunnel
(ngrok) presents as `https` while uvicorn itself only sees plain `http` —
signature validation fails silently if this mismatch isn't corrected for.

---

## 10. Every webhook branch returns valid TwiML — never a bare 500

**Decision:** the entire message-handling body in
`whatsapp_webhook()` is wrapped in `try/except`, and every branch — no
input, a tool error, an Anthropic API failure, a media-fetch failure —
ends by building a `MessagingResponse` and returning it as XML.

**Why:** on WhatsApp, a webhook that 500s and a webhook the user never gets
a reply from look identical from the user's side — silence. Always
returning *some* TwiML means the user always sees a message, even if it's
"something went wrong, try again," which is a categorically better failure
mode than nothing.

---

## 11. `decode_emi_offer` delegates to `calculate_emi` instead of re-deriving amortization

**Decision:** when a checkout offer states a real (non-zero) interest
rate, `decode_emi_offer` calls `calculate_emi()` for the amortization math
rather than reimplementing reducing-balance EMI calculation.

**Why:** one tested, correct implementation of the EMI formula
(`calculate_emi`, pinned by `test_emi_known_value`) is safer than two
formulas that could quietly drift apart. `decode_emi_offer`'s genuinely new
math is narrow: stacking a processing-fee-plus-GST and a forfeited
discount on top of whichever total (financed or sticker-price) applies.

---

## 12. Testing strategy: three tiers, cheapest-first, nothing costs money by accident

**Decision:**
- `tests/test_tools.py`, `tests/test_whatsapp.py`'s two webhook tests —
  fully deterministic, no network, no API key, always run.
- `tests/test_agents.py`'s structural test (graph shape) — no network,
  always runs.
- `tests/test_agents.py`'s routing test — makes a real, billed API call,
  gated behind `pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"))`.

**Why:** `python -m pytest tests/ -q` should always be safe to run without
thinking about whether it'll hit a real API or cost money. Only tests that
explicitly need a live model self-select out when no key is configured,
rather than every test needing to be run with `-k` filters to avoid
surprises.

**Note:** `tests/test_whatsapp.py`'s two tests cover signature validation
and the no-input branch only — a live multimodal agent reply (the actual
"read a screenshot and decode the offer" path) has no automated test yet
and is verified by hand (see `product-brief.md`'s verification steps).
That's a real, currently-open gap, not an oversight to gloss over.

---

## 13. Two separate tool-schema formats for the same underlying functions

**Decision:** `tools/schemas.py` hand-writes Anthropic's JSON schema
format for Phase 1/WhatsApp. `agents/tools.py` uses LangChain's `@tool`
decorator (schema inferred from type hints + docstring) for Phase 2. Same
`tools/finance_tools.py` functions underneath both.

**Why:** each framework wants tool descriptions in its own shape; rather
than trying to share one format across both, each surface gets its own,
kept consistent in *wording* by convention (see the comment at the top of
`agents/tools.py`) but not by any shared source of truth.

**Cost:** the same "kept in sync by hand" risk as decision 2, one layer up
— a tool description improved in `schemas.py` doesn't automatically flow
into `agents/tools.py`'s docstring, or vice versa.

---

## 14. `requirements.txt` grows additively across phases, doesn't prune

**Decision:** [requirements.txt](../requirements.txt) is split into three
labeled sections — Phase 1, Phase 2 (marked "not currently used... kept
installed, not retired"), and the WhatsApp MVP — rather than removing
Phase 2's dependencies now that it's not the product direction.

**Why:** Phase 2 isn't formally retired (see decision 5), just unused — 
removing its dependencies would make `chat.py` stop working for no product
reason, purely a cleanup one. The comments make the *why* of each section
explicit so a future prune is a decision, not an accident.

---

## 15. Dashboard reads SQLite directly off disk — no API layer, no auth

**Decision:** `dashboard/` (a separate Next.js project) queries
`data/finbuddy.db` directly via `better-sqlite3` in server-only code
(`dashboard/src/lib/db.ts`). No FastAPI endpoints were added to
`whatsapp/webhook.py` for this, and the dashboard has no login.

**Why:** the dashboard is for one person (you), running locally, purely to
look at conversations/tool-call logs — building and securing a real API
surface for that would be work with no one but you to benefit from it
yet. Reading the file directly is the smallest thing that actually works,
consistent with how every other piece of this repo has been scoped (Phase
1's REPL, the WhatsApp MVP's Twilio Sandbox, etc.).

**Cost — a real coupling, not a hidden one:** the dashboard and the
WhatsApp bot must run on the same machine, sharing the same `data/` path.
That's fine today; it stops being fine the moment either process needs to
run somewhere the other can't reach its disk (e.g. deploying the bot to a
server while running the dashboard locally). At that point this decision
needs revisiting — likely into a small read-only API on the FastAPI side —
not before.

**Also:** `data/finbuddy.db` is written by two different processes —
`whatsapp/storage.py` (the `messages`/`tool_calls` tables, plain
structured logs for the dashboard) and `whatsapp/agent.py`'s `SqliteSaver`
checkpointer (`checkpoints`/`writes` tables, LangGraph's own schema, for
agent memory) — sharing one file rather than two, because they're the same
underlying "what happened in this thread" data, just shaped for different
readers (a human via the dashboard vs. the agent replaying its own state).

---

## 16. `web/` + `api/` — a public website, with a real API boundary instead of `dashboard/`'s direct-file-read pattern

**Decision:** the distribution plan changed (see `product-brief.md`'s
Distribution section, revised 2026-08-29) — a public website (`web/`,
Next.js + Clerk auth) is now the primary product surface, with WhatsApp
continuing as a secondary/backend channel. `web/` does **not** read
`data/finbuddy.db` directly the way `dashboard/` does; it calls a new
FastAPI service (`api/main.py`) which is the one that imports
`tools/finance_tools.py`.

**Why not extend `dashboard/` itself:** `dashboard/` was explicitly
justified as "you, locally, no auth" (decision 15) — a public app with
real user accounts and other people's financial data is a different
security posture, not a login screen bolted onto the same codebase. `web/`
is a sibling app, seeded from `dashboard/`'s already-working stack
(Next.js 16, Tailwind v4) rather than seeding from scratch.

**Why a real API instead of direct SQLite reads:** decision 15's own
"Cost" section already named this — direct-file-read stops being
appropriate "the moment either process needs to run somewhere the other
can't reach its disk," which a public multi-user product guarantees will
happen eventually (`web/` on Vercel, the backend elsewhere). Building the
API boundary now, while the surface area is small (one endpoint), is
cheaper than retrofitting it later once `dashboard/`'s pattern has spread
further.

**Why a separate FastAPI app from `whatsapp/webhook.py`, not new routes on
it:** that file is Twilio-specific — TwiML replies, webhook signature
validation against `TWILIO_AUTH_TOKEN`. `api/main.py` serves a browser
directly with plain JSON and CORS, a different contract entirely. Same
"one job per file" reasoning as every other split in this repo.

**What's live vs. scaffolded (2026-08-29):** `api/main.py`'s
`/decode-offer` endpoint is real and tested (matches
`test_decode_emi_offer_hidden_processing_fee`'s known values exactly,
verified via `TestClient`). `web/` has a landing page, a working
`/decode` page wired to that endpoint, and Clerk auth scaffolded
end-to-end (sign-in button, `auth()`-gated header) — but Clerk needs real
API keys in `web/.env.local` (copy from `.env.local.example`) before
sign-in actually works; it currently 500s on the placeholder keys, same
credential-not-yet-added pattern as Twilio/ngrok before it. Auth-gated
profile/history endpoints (the actual point of having accounts — reusing
`tools/user_profile.py`'s tier-3 memory work) don't exist yet.

**A `/decode-offer` is deliberately not behind auth:** same reasoning as
the WhatsApp bot — the core "is this EMI actually free" answer shouldn't
require an account, only saving/recalling a profile should.

**Two version-drift traps hit and fixed while building this, worth knowing
about if either package gets upgraded again:** the installed Next.js
(16.3.3) deprecated the `middleware.ts` file convention in favor of
`proxy.ts` mid-build; and the installed `@clerk/nextjs` (7.8.3, "Core 3")
removed the `<SignedIn>`/`<SignedOut>` components entirely — they now
throw at render time by design (see
`node_modules/@clerk/nextjs/dist/.../removedControlComponents.js`).
`web/app/layout.tsx` uses `auth()` from `@clerk/nextjs/server` instead,
which isn't removed. Both `web/AGENTS.md` and `web/CLAUDE.md` (auto-managed
by `next dev`) flag that this Next.js version has breaking changes from
older training data — worth reading before assuming any remembered Next.js
API still applies here.

# FinBuddy — Learnings

Not a decision log (`decision.md`) or a runtime trace (`flow.md`) — this is
the "what to actually take away from reading this code" file: mental
models, comparisons between the three implementations sitting side by side
in this repo, and a glossary for the domain terms. Read after `flow.md`
once you've seen the code run at least once.

## Recommended reading order

1. `agent/agent.py` — the whole agentic pattern in ~80 lines. Everything
   else in this repo is elaboration on this file.
2. `tools/finance_tools.py` + `tools/schemas.py` — the four/five tools and
   what the model is told about them.
3. `whatsapp/prompts.py` + `whatsapp/webhook.py` — the current product,
   and the smallest possible "new channel" built on top of #1.
4. `agents/orchestrator.py` + `agents/credit_debt_agent.py` — the same
   idea as #1, through a framework, for comparison.
5. The three `tests/*.py` files — what's actually verified vs. trusted.

---

## 1. An "agent" is one loop, repeated

Strip away every framework, and every tool-calling LLM agent is: send the
conversation + a list of tools the model may call → the model replies with
either plain text or a request to call specific tools with specific
arguments → you execute those, hand the results back → repeat until you
get plain text. `agent/agent.py:FinanceAgent.chat` (see `flow.md`, Flow 1)
*is* this loop, unhidden. LangGraph's `create_react_agent` (Phase 2) and a
future MCP-based setup are the same loop with more machinery around it —
not a different idea.

## 2. Tool descriptions are prompts, steering behavior, not documentation

`tools/schemas.py`'s `description` fields (and `agents/tools.py`'s
docstrings, which play the identical role for Phase 2) are read by the
model at decision time to decide *whether* and *how* to call a tool.
`affordability_check`'s description literally contains the instruction
"Ask the user for their monthly net income and existing EMIs first if you
don't know them" — that sentence, not any code, is what makes the model
ask instead of guessing. Edit it and the model's behavior changes with no
code change at all. Worth deliberately breaking this once (loosen the
wording, watch the model start guessing numbers) to feel how load-bearing
these strings are.

## 3. Conversation state lives in a list, not in tool code

Every tool in `tools/finance_tools.py` is a pure function — no memory, no
side effects (except `get_stock_quote`'s network call). All conversational
memory is `FinanceAgent.messages`, a plain list mutated in place. This is
why `whatsapp/webhook.py` needs one `FinanceAgent` object *per sender*
(`SESSIONS: dict[str, FinanceAgent]`) — a session is nothing more than "an
object holding a growing list," and giving each sender their own instance
is the entire mechanism keeping conversations from bleeding into each
other. There's no database here; the list *is* the state, and it's gone
when the process restarts.

## 4. "Never let it crash" is the same philosophy, applied three times, three different shapes

- Tool level (`agent/agent.py:_execute_tool`): an exception becomes
  `{"error": ...}` JSON handed back to the *model*, which can react to it.
- REPL level (`chat.py`'s Phase 2 loop): an exception during a whole graph
  invocation gets the unrecorded user turn popped back off, an error
  printed to the *user*, and the loop kept alive.
- Webhook level (`whatsapp/webhook.py`): an exception anywhere in message
  handling still produces valid TwiML, because on WhatsApp a crash and
  silence are indistinguishable to the user.

Same instinct — the failure boundary should never propagate further than
it has to — applied at whichever layer actually owns the risk at that
point. Worth noticing this pattern repeats rather than treating each as a
one-off.

## 5. Hand-rolled loop vs. framework loop — a real, readable comparison

Phase 1 (`agent/agent.py`) and Phase 2's specialists
(`agents/credit_debt_agent.py`, via `create_react_agent`) implement the
*same* loop. Reading both back to back is the fastest way to see what
`langgraph.prebuilt.create_react_agent` is actually doing under the hood —
it's not a different pattern, it's Phase 1's loop with the tool-execution
and message-management boilerplate abstracted away. What the framework
adds on top: `create_supervisor`'s handoff-as-tool-call routing
(`agents/orchestrator.py`), which *would* be real hand-rolled work to build
yourself (a router deciding which specialist gets a message, and passing
control + context between them). That's the actual value framework buys
here — not the loop itself.

## 6. A well-built primitive absorbs new requirements without changing

`FinanceAgent.chat`'s `user_message: str | list[dict]` signature was
general from the start — "content" is whatever shape the Anthropic API
accepts, not specifically "a string." When the WhatsApp MVP needed to
handle a forwarded image (a multimodal message: an image block + a text
block), `whatsapp/webhook.py` could build that list and hand it straight
to the *unmodified* `chat()` method (`flow.md`, Flow 5) — no new parameter,
no branching inside the loop. The lesson isn't "always support every
possible input type" — it's noticing that keeping a primitive's interface
as general as the underlying API actually is (rather than narrowing it to
today's one use case) is what made tomorrow's use case free.

## 7. Security details that are easy to skip, and how this repo flags them instead of hiding them

`whatsapp/webhook.py` validates `X-Twilio-Signature` against
`TWILIO_AUTH_TOKEN` before doing anything else — without it, anyone who
finds the webhook URL can POST fake messages and spend your Anthropic API
budget. The dev-mode bypass (skip validation if no token is configured
yet) is real and necessary for local development, but it's marked inline
with `# don't deploy like this` rather than silently becoming the default
path. Good habit to copy: a convenience shortcut taken during development
should say out loud that it's a shortcut, at the point it's taken — not
rely on someone remembering later.

## 8. Two schema formats, one source of truth for the math

`tools/schemas.py` (raw Anthropic JSON schema, hand-written) and
`agents/tools.py` (LangChain `@tool`, schema inferred from type hints +
docstring) describe the *same* functions to two different model-calling
surfaces. Neither ever reimplements the math — both call straight into
`tools/finance_tools.py`. This is deliberate: whatever framework or API
format a tool needs to be described in, there is exactly one place the
actual calculation logic can live and be tested. If you ever add a tool,
the rule is "logic in `finance_tools.py` first, then wrap/describe it for
whichever surface(s) need it" — never the reverse.

## 9. Correctness comes from tests pinning known values, not from the formula looking right

`test_emi_known_value` doesn't just check "an EMI came back" — it asserts
`calculate_emi(1_000_000, 10, 60)["emi"]` is within ₹1 of `21247.04`, a
value that can be checked against any bank's own EMI calculator.
`decode_emi_offer`'s tests pin an exact GST-inclusive processing-fee figure
(`588.82` on a ₹499 fee at 18% GST). This matters more for money math than
most code: a formula that's subtly wrong (off-by-one in compounding, wrong
GST base) still returns a plausible-looking number, so "does it look
reasonable" isn't a real check — only a pinned, independently-verifiable
value is.

## 10. New tools are built by delegating to existing ones, not by copy-pasting formulas

`decode_emi_offer` doesn't reimplement reducing-balance amortization for
the case where an offer states real interest — it calls `calculate_emi`
and adds the fee/discount stacking on top. If `calculate_emi`'s formula
is ever fixed or improved, `decode_emi_offer` inherits that fix for free
instead of silently keeping the old, wrong math. Worth checking any new
tool you add against this question: does this genuinely need new math, or
does it need existing math plus one new step?

## 11. What actually changed to go from "REPL demo" to "shippable product"

Almost nothing at the agent level. Compare `main.py` + `agent/agent.py`'s
default `SYSTEM_PROMPT` to `whatsapp/webhook.py` +
`whatsapp/prompts.py`'s `CHECKOUT_SYSTEM_PROMPT`: same class, same loop,
same tool-dispatch mechanism — a different system prompt (a different
*persona* for a different moment) and one new tool
(`decode_emi_offer`). The real engineering work was the distribution
channel (a FastAPI webhook, Twilio signature validation, fetching
protected media, TwiML replies) — not the "agent" part, which had already
been proven out in Phase 1. That's a fairly general lesson about this kind
of build: get the core loop right early and cheaply (a REPL), and the
"real" channel can be a thin adapter instead of a rewrite.

## 12. Known, real gaps — not glossed over

- No test exercises a live multimodal reply (Flow 5) — signature
  validation and the no-input branch are the only things
  `tests/test_whatsapp.py` automates; verifying "forward a screenshot, get
  a correct decoded cost" currently means doing it by hand.
- Nothing enforces that `tools/finance_tools.py`'s `TOOL_FUNCTIONS`,
  `tools/schemas.py`'s `TOOL_SCHEMAS`, and `agents/tools.py`'s wrappers
  stay in sync — three manually-maintained lists describing the same
  underlying functions.
- `WhatsApp` sessions are in-memory only; a server restart loses every
  active conversation.
- Phase 2 is unused but not retired — still installed, still tested,
  still in the repo, a live decision not yet made (see `decision.md` #5,
  #14).

---

## Glossary

- **EMI (Equated Monthly Installment):** a fixed monthly loan repayment
  covering both principal and interest, computed via the reducing-balance
  formula in `calculate_emi`.
- **Reducing-balance:** interest each month is charged on the *remaining*
  principal, not the original amount — the standard method Indian lenders
  use; contrast with flat-rate interest (rare, usually a red flag).
- **FOIR (Fixed Obligation to Income Ratio):** total monthly loan/EMI
  obligations divided by net monthly income — the ratio Indian lenders use
  to gate loan approval. `affordability_check` uses 40%/50% thresholds for
  "comfortable"/"stretched"/"not advisable."
- **No-cost EMI:** a checkout offer with 0% *stated* interest — but
  "no-cost" often still hides a processing fee (plus GST on it) or a
  forfeited discount/cashback only available on full payment. This is
  exactly what `decode_emi_offer` computes.
- **`tool_use` / `tool_result`:** Anthropic Messages API content block
  types — a `tool_use` block is the model requesting a tool call with
  specific arguments; a `tool_result` block is your code's answer, sent
  back as a new user turn.
- **ReAct (Reason + Act):** the pattern of alternating "the model reasons
  about what to do" and "the model acts by calling a tool," repeated until
  done — what `agent/agent.py`'s loop implements by hand, and what
  `langgraph.prebuilt.create_react_agent` provides pre-built.
- **Supervisor (LangGraph):** an LLM node whose only job is choosing which
  other agent/node should handle a message, implemented as the supervisor
  calling a `transfer_to_<agent>` tool — routing is just another instance
  of "model picks a tool."
- **TwiML:** the XML response format Twilio's webhook contract requires —
  `whatsapp/webhook.py` must return a `<Response><Message>...` document,
  not a plain JSON/text body, for Twilio to relay a reply back to
  WhatsApp.
- **SEBI RIA (Registered Investment Adviser):** the registration India's
  securities regulator requires before anyone can give personalized "buy/
  invest in X" recommendations — why every system prompt in this repo
  explicitly says "information and education, not personalized advice."

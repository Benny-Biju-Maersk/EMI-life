# FinBuddy — Runtime Flows

Step-by-step traces of what actually executes, for each entry point in the
repo. Read [decision.md](decision.md) alongside this for *why* each step is
shaped the way it is — this file is just *what happens, in order*.

All three entry points (`main.py`, `chat.py`, `whatsapp/webhook.py`)
eventually run through `FinanceAgent.chat()` in
[agent/agent.py](../agent/agent.py) — Flow 4/5 (WhatsApp) is not a separate
agent, it's the same loop as Flow 1/2 with different inputs. Phase 2
(Flow 3) is the one genuinely different loop, provided by LangGraph instead
of hand-rolled.

---

## Flow 1 — Phase 1 REPL, single tool call

`python main.py`, user types: `"EMI on a 5 lakh loan at 10% for 24 months?"`

1. [main.py:26](../main.py) — `reply = agent.chat(user)`.
2. [agent/agent.py:77](../agent/agent.py) — `self.messages.append({"role": "user", "content": "EMI on a..."})`.
   First turn, so `self.messages` is now `[{user turn}]`.
3. [agent/agent.py:80-86](../agent/agent.py) — loop iteration 1:
   `self.client.messages.create(model=MODEL, system=SYSTEM_PROMPT,
   tools=TOOL_SCHEMAS, messages=self.messages)`. The model sees all four
   Phase-1 tool schemas and the system prompt's rule "use tools for any
   calculation."
4. Model responds with `stop_reason == "tool_use"`, content includes a
   `tool_use` block: `{name: "calculate_emi", input: {principal: 500000,
   annual_rate_pct: 10, tenure_months: 24}, id: "toolu_..."}`.
5. [agent/agent.py:89](../agent/agent.py) — the full assistant turn
   (including the `tool_use` block) is appended to `self.messages` exactly
   as returned.
6. [agent/agent.py:91](../agent/agent.py) — `stop_reason != "tool_use"` is
   false, so the loop doesn't return yet; it executes tools instead.
7. [agent/agent.py:96-99](../agent/agent.py) — for the `tool_use` block:
   prints `  [tool] calculate_emi({"principal": 500000, ...})`, calls
   `self._execute_tool("calculate_emi", {...})`.
8. [agent/agent.py:62-70](../agent/agent.py) —
   `TOOL_FUNCTIONS["calculate_emi"]` is
   `tools/finance_tools.py:calculate_emi`. It runs the reducing-balance
   formula, returns a dict, which gets `json.dumps`'d.
9. [agent/agent.py:100-106](../agent/agent.py) — a `tool_result` block is
   built: `{type: "tool_result", tool_use_id: "toolu_...", content:
   '{"emi": 23071.31, ...}'}`.
10. [agent/agent.py:107](../agent/agent.py) — a new `user` message
    containing just that `tool_result` block is appended to
    `self.messages`.
11. Loop iteration 2: `messages.create(...)` is called again, now with the
    full history (user question → assistant tool call → tool result).
    The model reads the EMI numbers and writes a plain-text answer.
12. `stop_reason == "end_turn"` this time, so
    [agent/agent.py:92](../agent/agent.py) returns the concatenated text
    blocks.
13. [main.py:27](../main.py) prints `finbuddy > <answer>`.

**State after this turn:** `self.messages` now holds 4 entries (user
question, assistant tool-call turn, user tool-result turn, assistant final
answer) — this *is* the conversation memory; nothing else stores it.

---

## Flow 2 — Phase 1 REPL, model asks a clarifying question first

`python main.py`, user types: `"Can I afford a 1.2L phone on 12-month EMI?"`
(no income given).

1-3. Same as Flow 1 up to the first `messages.create()` call.
4. Per `SYSTEM_PROMPT`'s rule ("If you need the user's income or existing
   EMIs for an affordability check, ask for them before calling the
   tool"), the model does **not** emit a `tool_use` block this turn — it
   returns plain text asking for income and existing EMIs.
   `stop_reason == "end_turn"` immediately, no tool round happens.
5. [agent/agent.py:92](../agent/agent.py) returns that question as-is;
   `main.py` prints it.
6. User types their answer, e.g. `"90k income, 15k in other EMIs"`.
7. [main.py:26](../main.py) calls `agent.chat(...)` **again**, on the
   *same* `FinanceAgent` instance — `self.messages` already has the first
   Q&A in it, so this new user turn is appended on top, and the model now
   has enough context to call `affordability_check` in this second
   `chat()` call, following Flow 1's tool-call path from here.

**Why this matters:** this is the behavior README's exercise 1 asks you to
break on purpose — the "ask before guessing" rule lives only in
`SYSTEM_PROMPT`'s English, not in code. Loosen the schema description or
system prompt and the model may guess a number instead of asking; nothing
in the loop itself prevents that.

---

## Flow 3 — Phase 2 multi-agent (`chat.py`), unused product direction

`python chat.py`, user types: `"What's the EMI on a 5 lakh loan at 10% for 24 months?"`

1. [chat.py:56](../chat.py) — `messages.append({"role": "user", "content": user})`.
2. [chat.py:59](../chat.py) — `graph.stream({"messages": messages})`. The
   compiled graph from [agents/orchestrator.py](../agents/orchestrator.py)
   starts at its `supervisor` node.
3. **Supervisor node:** the supervisor LLM (given `SUPERVISOR_PROMPT` and
   two auto-added tools, `transfer_to_credit_debt_agent` /
   `transfer_to_markets_agent`) reads the question and — per its prompt's
   routing rule — calls `transfer_to_credit_debt_agent`. This is a normal
   tool call from the supervisor's point of view; `create_supervisor`
   turns that tool call into an actual handoff.
4. **`credit_debt_agent` node:** this is a
   `langgraph.prebuilt.create_react_agent` — internally it runs its *own*
   model → tool-call → tool-result → model loop, structurally identical to
   Flow 1 steps 3-11, just implemented by the framework instead of by
   hand. It calls `calculate_emi_tool`
   ([agents/tools.py](../agents/tools.py)), which itself just calls
   `tools/finance_tools.py:calculate_emi` and `json.dumps`s the result —
   same underlying math as Flow 1.
5. Control returns to the supervisor, which relays the specialist's answer
   as the final response (per `SUPERVISOR_PROMPT`: hand off to one
   specialist unless the question spans both).
6. [chat.py:25-38](../chat.py) — `_print_trace()` runs on every streamed
   chunk, printing `[supervisor] -> transfer_to_credit_debt_agent(...)` and
   `[credit_debt_agent] -> calculate_emi_tool(...)` as they happen — this
   is Phase 2's equivalent of Flow 1's `[tool] ...` print, since routing
   would otherwise be invisible.
7. [chat.py:63-66](../chat.py) — the full updated `messages` list is
   pulled from whichever node ran last, replacing `chat.py`'s local
   `messages` variable (unlike Phase 1, state isn't held inside an object
   automatically — `chat.py` has to reassign it every turn).

**Error path:** [chat.py:68-74](../chat.py) — if anything in the graph
invocation raises (rate limit, billing issue, network error), the just-appended
user message is popped back off `messages` and an inline error is printed,
so the next turn starts from clean, uncorrupted history rather than
carrying a half-failed turn forward.

---

## Flow 4 — WhatsApp webhook, plain text message

User forwards nothing but types a WhatsApp message: `"Should I take a
12-month no-cost EMI on a ₹40,000 TV, ₹499 processing fee?"`

1. Twilio POSTs form-encoded data to `/whatsapp`
   ([whatsapp/webhook.py:63](../whatsapp/webhook.py)).
2. [whatsapp/webhook.py:68-75](../whatsapp/webhook.py) — if
   `TWILIO_AUTH_TOKEN` is set, `RequestValidator` checks
   `X-Twilio-Signature` against the reconstructed request URL
   (`_request_url()`, correcting for a tunnel's forwarded headers). A bad
   signature returns `403` immediately — nothing past this point runs.
3. [whatsapp/webhook.py:77-79](../whatsapp/webhook.py) — `from_number`,
   `body`, `num_media` are pulled from the form. `num_media == 0` here.
4. [whatsapp/webhook.py:100-101](../whatsapp/webhook.py) — since `body` is
   non-empty, `content = body` (a plain string).
5. [whatsapp/webhook.py:110](../whatsapp/webhook.py) —
   `_get_session(from_number)`: looks up or creates a `FinanceAgent` in
   `SESSIONS`, constructed with `system_prompt=CHECKOUT_SYSTEM_PROMPT`
   ([whatsapp/prompts.py](../whatsapp/prompts.py)) instead of Phase 1's
   default.
6. [whatsapp/webhook.py:111](../whatsapp/webhook.py) —
   `session.chat(content)` — from here it's **exactly Flow 1's loop**,
   just with `CHECKOUT_SYSTEM_PROMPT` steering the model and
   `decode_emi_offer` (plus `affordability_check`) available as tools. The
   model, per that prompt, calls `decode_emi_offer(item_price=40000,
   tenure_months=12, processing_fee=499, ...)`.
7. [whatsapp/webhook.py:118-120](../whatsapp/webhook.py) — the returned
   text is wrapped: `twiml.message(reply_text)`, returned as
   `application/xml` — this is the shape Twilio's webhook contract
   requires, not a normal HTTP response body.

---

## Flow 5 — WhatsApp webhook, forwarded screenshot (multimodal)

User forwards a screenshot of a checkout EMI offer, no caption.

1-3. Same as Flow 4, except `num_media == 1` and `MediaUrl0`/
   `MediaContentType0` are present in the form.
4. [whatsapp/webhook.py:84-99](../whatsapp/webhook.py) — `media_url =
   params["MediaUrl0"]`. An `httpx.AsyncClient` fetches it with HTTP basic
   auth (`TWILIO_ACCOUNT_SID`/`TWILIO_AUTH_TOKEN`) — Twilio's media URLs
   are access-protected, not public. The response bytes are
   base64-encoded into `image_b64`.
5. `content` is built as a **list**, not a string:
   `[{"type": "image", "source": {"type": "base64", "media_type":
   media_type, "data": image_b64}}, {"type": "text", "text": body or
   "Please evaluate this EMI/BNPL offer."}]`.
6. [whatsapp/webhook.py:110-111](../whatsapp/webhook.py) — same
   `_get_session()` + `session.chat(content)` call as Flow 4, but now
   `content` is that list, not a string.
7. [agent/agent.py:72-77](../agent/agent.py) — `FinanceAgent.chat`'s
   `user_message: str | list[dict]` parameter accepts this without any
   special-casing — `self.messages.append({"role": "user", "content":
   user_message})` stores the list exactly as it would a string. This is
   decision 7 in `decision.md` paying off: the loop needed zero changes to
   support this.
8. The model call includes the image directly. Per
   `CHECKOUT_SYSTEM_PROMPT`'s rules, the model reads item price, tenure,
   and any visible fee/discount off the image itself, and either:
   - has everything it needs → calls `decode_emi_offer` directly
     (Flow 4's tool-call path from here), or
   - is missing something that matters (e.g. no processing fee is
     visible, but the prompt says never assume zero) → asks a clarifying
     text question instead, ending the turn without a tool call — the
     user answers by text, hitting Flow 4 on the next incoming message
     with the same session (so context — that this was about the
     forwarded screenshot — persists via `self.messages`).

---

## Flow 6 — error paths (all three entry points)

Three different "something went wrong" boundaries exist, each shaped by
what's actually being protected:

1. **A single tool call fails** (bad input, `yfinance` network error, a
   real bug) — [agent/agent.py:62-70](../agent/agent.py) catches it inside
   `_execute_tool`, returns `{"error": "..."}` as the tool result. The
   *model* sees this, not the user directly — it can explain or retry with
   different input. The conversation continues normally.
2. **Phase 2's whole graph invocation fails** (rate limit, billing,
   network) — [chat.py:68-74](../chat.py) catches it at the REPL level,
   pops the unrecorded user turn off `messages`, prints an inline error,
   and keeps the REPL loop alive for the next question with clean history.
3. **The WhatsApp webhook's whole request fails** (media fetch fails, the
   Anthropic call fails, anything) —
   [whatsapp/webhook.py:82-116](../whatsapp/webhook.py) catches it around
   the entire message-handling body and falls back to a generic
   `reply_text`, but **still returns valid TwiML** rather than a bare
   500 — see decision.md's point 10 for why that distinction matters on
   WhatsApp specifically (a 500 and silence look identical to the user).

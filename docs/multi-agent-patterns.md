# Multi-Agent Patterns — Behavior, Memory, Context, Action-Taking

A deeper pass on the four concepts from our conversation, worked entirely
against code already in this repo, plus a design checklist for adding a
new specialist to the "single portal for all finance" vision. Read
[learnings.md](learnings.md) first if you haven't — this file assumes you
already know the base ReAct loop.

The hands-on companion to this doc is `agents/budget_agent.py` — a third
specialist added specifically to give tier-3 memory (below) a real,
runnable example, since nothing else in the repo needed it yet.

---

## 0. The one insight everything else follows from

A "supervisor" is not special routing logic. `agents/orchestrator.py`'s
`create_supervisor` gives the supervisor LLM two auto-generated tools —
`transfer_to_credit_debt_agent`, `transfer_to_markets_agent` — and the
supervisor picks between them using the *exact same* tool-choice mechanism
`calculate_emi` gets picked by inside a specialist. Multi-agent is single-agent,
one level up. Once that's internalized, "how do I design a multi-agent
system" becomes "how do I decide what counts as a tool at each level" —
which is a much more concrete question.

---

## 1. Behavior — where an agent's identity actually lives

Every agent in this repo is fully described by two things:

```
behavior = system_prompt (rules, scope, tone, compliance framing)
         + tool_list     (what it's even capable of doing)
```

Nothing else varies agent-to-agent — not the loop, not the model class, not
the message format. Compare:

- `agents/credit_debt_agent.py` — scoped to EMI/prepayment/affordability,
  tools = `CREDIT_DEBT_TOOLS`.
- `agents/markets_agent.py` — scoped to price data only, explicit "never
  recommend buy/sell" rule, tools = `MARKETS_TOOLS`.
- `whatsapp/prompts.py`'s `CHECKOUT_SYSTEM_PROMPT` — same loop class
  entirely (`FinanceAgent`, Phase 1's, not even Phase 2's), scoped to one
  moment (a checkout decision) rather than one domain.

**Design principle for splitting agents:** the credit_debt/markets split in
this repo is a *domain* split (what subject matter). The WhatsApp persona
is a *moment* split (what point in the user's day). Both are valid axes —
pick whichever makes each agent's system prompt short and unambiguous. A
bad split produces a system prompt full of "except when..." — that's the
signal you split along the wrong axis, or split too early.

**Compliance boundaries deserve their own agent, not a shared prompt
clause.** `markets_agent.py`'s SEBI framing ("not investment advice") is
baked into every rule in its prompt, not appended as an afterthought — that's
deliberate: a compliance-sensitive domain benefits from an agent whose
*entire* prompt is written around the constraint, rather than one generic
agent trying to remember a rule that only matters for some of its answers.

---

## 2. Memory — three tiers, and this repo now has an example of each

Don't use "memory" as one word for three different mechanisms:

| Tier | Scope | Example in this repo | Survives... |
|---|---|---|---|
| **1. Conversational** | this thread only | `FinanceAgent.messages` (Phase 1); LangGraph's checkpointer (WhatsApp MVP) | multiple turns |
| **2. Persistent conversational** | this thread, across restarts | WhatsApp MVP's `SqliteSaver` (added specifically because `main.py`'s in-memory-only `messages` list wasn't enough for a real user coming back tomorrow) | process restarts |
| **3. Long-term profile** | *this user*, across every conversation/thread they'll ever have | **new** — `agents/budget_agent.py` + `tools/user_profile.py`, added as this doc's worked example | everything — it's not a transcript at all, it's structured facts |

Tier 1 and 2 are the same *kind* of memory (a replayable transcript),
differing only in whether it's durable. Tier 3 is a **different mechanism
entirely** — not "more turns remembered," but explicit, structured,
queryable facts (income, essential expenses) that any agent can read or
write via a tool call, independent of which conversation thread is active
right now.

**Decision framework for a new specialist:** ask "if the user starts a
brand new conversation tomorrow, does this agent need to already know
something from today?" If no — tier 1 (or 2, if it should survive a
restart) is enough. If yes — it needs tier 3, and the *tool interface* to
that store (not the conversation history) is how it gets that fact. This
is exactly why `budget_agent.py` needed something the other two
specialists didn't: "can I afford this EMI" needs the user's income
*right now, this conversation* (tier 1 is enough — `affordability_check`
takes income as a direct argument every time). "What's my monthly budget
looking like" needs the user's income *whether or not they've mentioned it
in this conversation* — that's a tier-3 read.

---

## 3. Context — what's actually in the window, and the shared-vs-scoped choice

At any single model call, context = system prompt + tool schemas + message
history + this turn's tool results. In a multi-agent graph, one extra
question appears that a single agent never has to answer: **when control
hands off, how much of the prior conversation does the next agent see?**

`agents/orchestrator.py`'s `create_supervisor` defaults to **shared
context** — a specialist sees the *entire* running message list, including
turns that had nothing to do with it. This is simple and usually fine at
this scale, but it's a real tradeoff, not a free win:

- **Shared context (what this repo does):** a specialist automatically has
  whatever the user said earlier, even to a different specialist. Cost:
  every specialist's prompt has to tolerate seeing irrelevant history
  without getting confused by it, and every call pays the token cost of
  the full transcript, whether or not it's relevant.
- **Scoped/private context (not implemented here):** the supervisor would
  explicitly extract and hand off *only* the facts relevant to the target
  specialist ("user is asking about affordability, income is ₹90k,
  existing EMIs ₹15k") instead of the raw transcript. Cost: real design
  work — someone (a prompt, or code) has to decide what's "relevant" at
  each handoff, and information not explicitly extracted is genuinely
  lost to the specialist.

`budget_agent.py` sidesteps this tradeoff for tier-3 facts specifically —
instead of relying on shared conversational context to carry the user's
income forward, it fetches it explicitly via a tool call
(`get_saved_profile`) every time it needs it. That's a general pattern
worth naming: **when a fact needs to survive past what conversational
context can guarantee, make it a tool call, not a hope that context
carries it far enough.**

---

## 4. Action-taking — the loop, and routing as its natural extension

Recap of the base loop (see `learnings.md` §1 for the single-agent
version): reason over context → emit a `tool_use` (act) or plain text
(conclude) → if acted, observe the result → repeat.

In a supervisor graph, this happens at **two nested levels** simultaneously:

1. **Supervisor level:** the supervisor reasons over the user's message,
   picks a `transfer_to_<agent>` tool (or, per `SUPERVISOR_PROMPT`, calls
   more than one if the question genuinely spans domains), and hands off.
2. **Specialist level:** once invoked, the specialist runs its *own*
   complete inner loop — reason → call a domain tool → observe → repeat —
   exactly like Phase 1's single agent, until it has a final answer, then
   returns control to the supervisor.

Nothing here is a different algorithm at the two levels — it's the same
loop, recursively, with "the tool" meaning something different at each
level. This is why adding a third specialist (`budget_agent.py`) required
touching almost nothing about *how* routing works — `create_supervisor`
auto-generates the new `transfer_to_budget_agent` tool the moment the agent
is added to the `agents=[...]` list; the supervisor's action-taking
mechanism didn't need to change, only its prompt's routing guidance did.

---

## 5. Checklist: adding a new specialist to the "single portal" vision

Concrete steps, in order, for whatever comes next (autopay, a real budgeting
specialist beyond the worked example, etc.) — this is the same sequence
`budget_agent.py` followed:

1. **Write the domain logic first**, in `tools/finance_tools.py` (or a new
   sibling module if it's not "finance math" — e.g. `tools/user_profile.py`
   for tier-3 storage) — plain, tested functions, no framework.
2. **Ask the tier question** (§2): does this specialist need facts that
   outlive one conversation? If yes, that's a tool-call-based read/write to
   a structured store, not something you can rely on conversational context
   to carry.
3. **Write the system prompt around one axis** (§1) — domain or moment,
   whichever keeps the prompt free of "except when" clauses. Put any
   compliance constraint as a first-class rule, not an addendum.
4. **Wrap the tools** for whichever surface(s) need them (`agents/tools.py`
   for LangChain/Phase 2, `tools/schemas.py` if Phase 1/WhatsApp should
   also get it) — logic never lives in the wrapper, only in step 1's
   module.
5. **Register the specialist** in `agents/orchestrator.py`'s
   `agents=[...]` list, and add one routing sentence to `SUPERVISOR_PROMPT`
   describing when to hand off to it.
6. **Decide the context question** (§3) only if shared context stops being
   good enough — e.g. if a specialist starts visibly confusing itself with
   irrelevant history from another specialist's turns. Don't build scoped
   handoff pre-emptively; this repo hasn't needed it yet.

---

## 6. A fifth axis: live external data isn't memory at all

`agents/research_agent.py` (added after this doc's first version) is worth
naming separately because it's easy to lump in with §2's memory tiers and
it genuinely isn't one. Its tool, `get_market_news_tool`
(`tools/web_research.py`), makes a live HTTP call to Google News' RSS feed
on every invocation — nothing is stored, nothing is remembered, and asking
the same question twice in a row can return different results because the
world changed, not because of anything the agent tracked.

Contrast the three specialists' relationship to "where does the answer
come from":

| Specialist | Answer comes from |
|---|---|
| `credit_debt_agent` | pure computation on numbers given *this turn* |
| `budget_agent` | tier-3 memory — facts FinBuddy was explicitly told and stored |
| `research_agent` | the live, current state of the outside world — never stored, never the same twice |

This matters for the same reason §1's behavior-splitting principle does:
`research_agent`'s system prompt has one rule none of the others need —
"never invent a headline or recall one from memory, always fetch" —
because a model asked for "the latest news on X" will happily *hallucinate
a plausible-sounding headline* from training data if not explicitly told
the tool call is mandatory, not optional. Live-data tools need this rule
stated explicitly; pure-computation tools (`calculate_emi`) don't have the
same failure mode, since there's no plausible-sounding wrong answer for
the model to fall back on instead of calling the tool.

**Design principle:** before adding a new tool, ask which of these three
categories it falls into — computed, remembered, or fetched-live — since
each implies a different thing the system prompt has to say to keep the
model honest about actually using it.

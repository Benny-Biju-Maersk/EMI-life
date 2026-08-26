# FinBuddy — Product Brief

Status: **direction decided, MVP not yet scoped.** This is the output of a
dedicated product-discovery session, held deliberately separate from
feature/architecture work, before continuing Phase 3 of the roadmap in
[README.md](../README.md). It supersedes that roadmap's assumptions where
they conflict — see "What this changes" at the bottom.

## The problem

**Who:** Urban India, roughly 22–32, salaried or steady gig income,
UPI/card-native. Already carrying 1–2 running EMIs or a revolving credit
card balance. Doesn't self-identify as "in debt" — sees "₹999/month, no
cost EMI" as ordinary, sensible budgeting. That self-perception is exactly
why the problem is subtle rather than obviously alarming to the person
living it.

**What happens:** At checkout — Amazon/Flipkart/Myntra, a card's EMI
conversion offer, BNPL products like Simpl/LazyPay — the user is nudged
into an EMI without seeing two things:

1. **The true cost.** "No cost EMI" frequently isn't cost-free: a
   processing fee plus GST on it, or an instant-discount/cashback that's
   only available on full payment and silently forfeited by choosing EMI.
2. **The combined obligation.** Nobody shows "this is your Nth active EMI
   — here's what your total monthly commitment becomes, and what share of
   your take-home that now is."

**Why the window is narrow:** the only point where this actually helps is
*pre-commitment*, at the moment of the click. After purchase, this problem
collapses into ordinary debt tracking — a different, more crowded, less
differentiated problem (CRED, bank apps, budgeting apps all live there
already).

## Why this is a real moat, not just a feature idea

Every party structurally positioned to build this has the wrong incentive:

- Banks/NBFCs and card networks earn interest/fees on EMI conversion.
- E-commerce platforms want the AOV lift EMI options give them.
- CRED monetizes via bill-pay and lending referrals — not incentivized to
  talk a user out of an EMI, and it's a dashboard product, not a
  point-of-decision one.

**An unbiased, no-conflict agent is the entire value proposition here**,
not a nice-to-have on top of a feature set. This has one direct
consequence for monetization (below): if FinBuddy ever earns money via
lending referrals or affiliate placement, it destroys the one thing users
are trusting it for. Treat that as a hard constraint, not a later
optimization.

## Distribution: WhatsApp bot

Chosen over a browser extension (tighter to the actual moment, but high
build/maintenance friction — breaks on any checkout UI change, and harder
to get installed) and a standalone app/PWA (relies on the user remembering
to open it before buying, which undercuts the entire "intercept the
impulsive moment" premise).

A WhatsApp bot has near-zero install friction, meets users where they
already are, and lets someone forward a screenshot of the checkout offer or
just ask "about to buy a ₹40k TV on 12-month no-cost EMI, should I?" — a
natural fit for the conversational tool-calling agent already built
(`agent/agent.py`'s request → tool_use → tool_result loop), just retriggered
over WhatsApp instead of a REPL.

## Monetization: savings-based subscription

A small direct subscription, pitched on quantifiable avoided cost — e.g.
"saved you ₹14,000 in avoidable EMI interest this year" — rather than
freemium usage caps or a B2B2C model (employer wellness benefit / NBFC
compliance tool), both of which risk diluting the unbiased-advisor position
depending on who ends up paying.

**Named risk, not yet validated:** the underlying assumption — that people
will pay to be told *not* to spend — is the single biggest unproven bet in
this plan. Worth testing early rather than assuming.

## North Star (beyond this brief's wedge)

The wedge above is an entry point, not the destination. The longer-term
vision is an app that can speak to "anything and everything about money,"
behaving according to each specific user rather than generically — which is
also, worth being honest about it, the exact positioning INDMoney, Jupiter,
Fi Money, and ET Money are already funded and fighting over. Building
toward "everything" as v1 is the most common way a solo-built idea like
this stalls: infinite scope, no sharp entry point, competing head-on with
well-capitalized incumbents on their own turf.

The wedge and the North Star aren't in tension, though — the wedge is how
the rest gets earned. To work at all, the checkout-EMI-trap agent needs a
per-user profile: income, existing EMIs, spending pattern (the
affordability/FOIR math already requires this). That same profile is the
foundation every subsequent "anything and everything about money" feature
would need anyway. **Decided sequencing: ship the wedge first, let it force
the per-user profile/memory layer into existence, then layer future
features — including the informational stock analyzer below — on top of
that same profile rather than each starting over.** This is roughly where
Phase 3 (SQLite/persistence) already sat in the original roadmap; it now
serves the wedge first rather than a generic hosted web app.

## Future feature: informational stock analyzer (not v1)

Raised as a second feature idea and scoped, but deliberately sequenced
*after* the wedge and its profile layer, not alongside it.

**Compliance line (decided, important):** personalized "you should invest
in X" recommendations require SEBI Investment Adviser registration under
the SEBI (Investment Adviser) Regulations, 2013 — not a gray area, and it
applies even to a free app. Decided posture is **informational only**:
fundamentals, news, technicals, opportunity-cost comparisons — never a
personalized buy/sell recommendation. This keeps the feature legal without
RIA registration and consistent with the no-conflict-of-interest position
the whole product is built on (see the checkout-EMI-trap moat above).

**What makes it different from Groww/Zerodha/Tickertape/Screener** (which
already do general stock analysis well, and which a generic version of this
feature can't out-compete): it plugs into the same per-user profile as the
wedge, so it surfaces what's relevant to *this* user's situation — e.g. a
stock/fund they follow dropping 8%, shown in the context of their existing
obligations — rather than being a general market dashboard.

## What survives from the current build

The affordability/FOIR math in [tools/finance_tools.py](../tools/finance_tools.py)
is directly reusable: it's the right primitive, aimed at the wrong moment
(a REPL calculator instead of a checkout-time gut-check). The missing piece
is a new "decode this EMI offer" capability — ideally reading a forwarded
screenshot to unpack true cost vs. the advertised "no cost" — ahead of
whatever wraps it for WhatsApp.

## What likely doesn't survive

The Phase 2 Credit/Debt-vs-Markets LangGraph multi-agent split
(`agents/`) and the stock-quotes tool don't obviously serve this persona or
this pain. Flagged as likely cuts — not yet decided or actioned, since
architecture wasn't in scope for this session.

## What this changes about the existing roadmap

The README's Phase 3 (FastAPI wrapper, SQLite profiles) and Phase 4
(monetized hosted web app, auth, Stripe) were written before this
direction existed, aimed at a general "roadmap" rather than this specific
wedge. They should be revisited against this brief rather than executed
as originally scoped — e.g. a WhatsApp-bot MVP has a different backend
shape than a hosted web app with Stripe billing.

## Open, not yet decided

- Exact MVP scope (what's the smallest version that actually intercepts a
  real checkout decision?)
- WhatsApp Business API integration approach
- How to validate willingness-to-pay before building further
- Whether/how to formally retire the Phase 2 multi-agent split and
  stock-quotes tool

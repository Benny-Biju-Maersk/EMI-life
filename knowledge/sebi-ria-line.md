# Why FinBuddy never gives personalized investment advice

This is the compliance line every markets/research-facing surface in this
repo is written around (see `agents/markets_agent.py`, `agents/research_agent.py`,
`docs/product-brief.md`'s "Future feature" section) — worth having as a
retrievable fact so the council/chat agents can explain *why*, not just
enforce it silently.

**The rule:** under India's SEBI (Investment Adviser) Regulations, 2013,
giving *personalized* investment advice — telling a specific person to
buy, sell, or hold a specific security given their specific situation —
legally requires registration as a SEBI Registered Investment Adviser
(RIA). This applies regardless of whether the advice is paid or free, and
regardless of the medium (chat, app, WhatsApp).

**What's still fine without RIA registration (informational):**
- Explaining what a stock's price/fundamentals data shows.
- General education — what a P/E ratio means, how diversification works,
  what an index fund is.
- News/context — what's being reported about a company or sector.
- Opportunity-cost framing — e.g. "this EMI's effective interest rate is
  X%; historically, equity markets have returned roughly Y% over long
  horizons" — a comparison of numbers, not a recommendation to act.

**What crosses the line (personalized advice, needs RIA):**
- "You should buy/sell/hold [security]."
- "Given your situation, invest in X instead of paying off this loan."
- Any verdict tailored to one user's specific portfolio/goals that names a
  specific action to take with a specific security.

**Why this is a hard constraint for FinBuddy specifically, not just legal
caution:** the whole product's value proposition is being the one party
in the checkout-EMI/BNPL chain with no incentive to push a user toward any
particular financial product. Crossing into personalized investment advice
would also mean picking up the same conflict-of-interest risk the product
is built to avoid (see `docs/decision.md`'s moat argument).

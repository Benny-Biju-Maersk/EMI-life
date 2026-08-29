# FinBuddy — website

The public product surface (see [../docs/product-brief.md](../docs/product-brief.md)'s
Distribution section, revised 2026-08-29). WhatsApp (`../whatsapp/`)
continues to exist for the checkout-interception moment specifically, but
this is now the primary place someone lands.

Seeded from `../dashboard/`'s stack (Next.js 16, Tailwind v4) since that
app already proved the setup — but this is a separate app, not a modified
`dashboard/`, because it has a real security posture `dashboard/`
deliberately doesn't need (public auth, other people's data). See
[../docs/decision.md](../docs/decision.md) #16 for the full reasoning.

## Setup

1. **Backend API first** — this app calls `../api/main.py`, not
   `data/finbuddy.db` directly (unlike `dashboard/`). From the repo root:
   ```bash
   pip install -r requirements.txt   # if not already done
   uvicorn api.main:app --reload --port 8001
   ```
2. **This app:**
   ```bash
   npm install     # already done if you're reading this after the initial scaffold
   cp .env.local.example .env.local
   ```
3. **Clerk keys** — sign up free at [dashboard.clerk.com](https://dashboard.clerk.com),
   create an application, copy the **Publishable key** and **Secret key**
   from API Keys into `.env.local`:
   ```
   NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
   CLERK_SECRET_KEY=sk_test_...
   ```
   Without real keys, the app 500s on every page — Clerk validates the key
   format at startup, not just when someone actually signs in.
4. **Run it:**
   ```bash
   npm run dev
   ```
   http://localhost:3000 — the landing page and `/decode` (the core "decode
   my EMI offer" tool) work as soon as the API (step 1) is running; sign-in
   additionally needs step 3.

## What exists today (2026-08-29)

- `/` — landing page
- `/decode` — the core tool: fill in a checkout offer's terms, get the true
  cost back from `api/main.py`'s `/decode-offer` (same
  `tools/finance_tools.py:decode_emi_offer` every other surface in this
  repo uses — no math lives here)
- Clerk auth wired (sign-in button, `auth()`-gated header) but nothing is
  actually gated behind it yet

## What's next, not yet built

- Auth-gated profile page (save/view income, essential expenses, existing
  EMIs — reusing `tools/user_profile.py`'s tier-3 memory store, built as a
  learning exercise in Phase 2's `agents/budget_agent.py` and now ready for
  real product use)
- Auth-gated history page (a user's own past decoded offers — scoped to
  them, unlike `dashboard/` which shows every conversation)
- `api/main.py` needs matching auth-gated endpoints for both, verifying a
  Clerk session server-side before touching `tools/user_profile.py`

## A version-drift note, since it's easy to lose

The installed Next.js (16.3.3) and `@clerk/nextjs` (7.8.3, "Core 3") both
have breaking changes from what training data typically assumes —
`middleware.ts` is deprecated in favor of `proxy.ts`, and
`<SignedIn>`/`<SignedOut>` were removed entirely in favor of `auth()` from
`@clerk/nextjs/server`. See `AGENTS.md` in this directory (auto-managed by
`next dev`, don't hand-edit) and `../docs/decision.md` #16 before assuming
a remembered API still applies here.

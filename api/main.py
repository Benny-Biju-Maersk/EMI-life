"""Public API for web/ — the same tools/*.py logic every other surface in
this repo shares (Phase 1's REPL, Phase 2, the WhatsApp MVP), exposed over
plain JSON so the dashboard's widgets can call it directly.

Deliberately a separate FastAPI app from whatsapp/webhook.py, not an extra
route bolted onto it: that file is Twilio-specific (TwiML replies, webhook
signature validation) and named for that job. This one serves a browser
(via web/'s widgets), and now genuinely two different trust levels of
endpoint — see the section split below.

Run with:
    uvicorn api.main:app --reload --port 8001

--- Two trust levels, not one ---

**Public** (decode-offer, calculate-emi, prepayment-impact, stock-quote,
market-news): stateless, no user identity involved, same reasoning as the
WhatsApp bot needing no account for the checkout-interception moment. Safe
for the browser to call directly.

**Internal** (profile, reminders): these read/write a specific user's
data (tools/user_profile.py, tools/reminders.py) and MUST NOT be callable
by an untrusted caller claiming an arbitrary user_id — anyone could read
anyone else's income otherwise. This API does not verify Clerk sessions
itself (that would mean duplicating Clerk's session verification in
Python). Instead, web/'s own Next.js server-side API routes
(app/api/profile/route.ts, app/api/reminders/route.ts) call auth() —
already verified server-side, same mechanism the signed-in header already
uses — and only THEN call these endpoints, passing the verified user_id
themselves. The browser never talks to these two endpoints directly.

**Known simplification, not glossed over:** on localhost this boundary is
enforced by nothing but "the browser doesn't know this port exists for
these routes" — anyone who discovers :8001 directly could still call
/profile with any user_id they like. Fine for local development; before
deploying anywhere reachable by someone else, this needs either a shared
internal secret between web/ and api/, or real Clerk JWT verification
here (e.g. via the clerk-backend-api package) instead of trusting the
caller. Same "don't deploy like this" spirit as whatsapp/webhook.py's
dev-mode signature-validation bypass.
"""

from __future__ import annotations

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Every other entry point in this repo (agent/agent.py, whatsapp/webhook.py)
# loads .env itself rather than assuming something upstream already did —
# this file was missing it, which is exactly why GROQ_API_KEY showed as
# unset when run via `uvicorn api.main:app` despite being in .env: nothing
# had actually loaded it into the process environment yet.
load_dotenv()

from tools.finance_tools import (
    affordability_check,
    calculate_emi,
    decode_emi_offer,
    get_stock_quote,
    prepayment_impact,
)
from tools.financial_profile import (
    get_expenses,
    get_loans,
    save_expenses,
    save_loans,
    total_monthly_emi,
    total_monthly_expenses,
)
from tools.personalized_insights import synthesize_personalized_update
from tools.reminders import create_reminder, get_reminders_for_user
from tools.user_profile import get_profile, save_profile_field
from tools.web_research import get_market_news

app = FastAPI(title="FinBuddy public API")

# web/ runs on a different origin (localhost:3000 in dev) than this API
# (localhost:8001) — CORS has to be explicit or the browser blocks the
# request entirely. Tighten allow_origins to the real deployed domain
# before this goes anywhere past local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Public endpoints — stateless, no user identity, safe for the browser
# ---------------------------------------------------------------------------


class DecodeOfferRequest(BaseModel):
    item_price: float
    tenure_months: int
    processing_fee: float = 0
    gst_on_fee_pct: float = 18.0
    forfeited_discount: float = 0
    stated_interest_pct: float = 0
    # Optional: when provided, the endpoint also returns an affordability
    # verdict, same as whatsapp/prompts.py's CHECKOUT_SYSTEM_PROMPT folding
    # affordability_check in when income is known.
    monthly_net_income: float | None = None
    existing_emis: float = 0


@app.post("/decode-offer")
def decode_offer(req: DecodeOfferRequest) -> dict:
    result = decode_emi_offer(
        req.item_price,
        req.tenure_months,
        req.processing_fee,
        req.gst_on_fee_pct,
        req.forfeited_discount,
        req.stated_interest_pct,
    )
    if "error" in result:
        return result

    if req.monthly_net_income is not None:
        result["affordability"] = affordability_check(
            req.monthly_net_income,
            req.existing_emis,
            req.item_price,
            tenure_months=req.tenure_months,
        )
    return result


class CalculateEmiRequest(BaseModel):
    principal: float
    annual_rate_pct: float
    tenure_months: int


@app.post("/calculate-emi")
def calculate_emi_endpoint(req: CalculateEmiRequest) -> dict:
    return calculate_emi(req.principal, req.annual_rate_pct, req.tenure_months)


class PrepaymentImpactRequest(BaseModel):
    principal: float
    annual_rate_pct: float
    tenure_months: int
    months_paid: int
    lumpsum: float


@app.post("/prepayment-impact")
def prepayment_impact_endpoint(req: PrepaymentImpactRequest) -> dict:
    return prepayment_impact(
        req.principal,
        req.annual_rate_pct,
        req.tenure_months,
        req.months_paid,
        req.lumpsum,
    )


@app.get("/stock-quote")
def stock_quote_endpoint(symbol: str = Query(..., min_length=1)) -> dict:
    return get_stock_quote(symbol)


@app.get("/market-news")
def market_news_endpoint(query: str = Query(..., min_length=1), max_results: int = 5) -> dict:
    return get_market_news(query, max_results)


# ---------------------------------------------------------------------------
# Internal endpoints — user-specific, trusted-caller-only (see module
# docstring). Called by web/'s server-side API routes, never the browser
# directly.
# ---------------------------------------------------------------------------


@app.get("/profile")
def get_profile_endpoint(user_id: str = Query(..., min_length=1)) -> dict:
    return {"user_id": user_id, "profile": get_profile(user_id)}


class SaveProfileFieldRequest(BaseModel):
    user_id: str
    field: str
    value: str


@app.post("/profile")
def save_profile_field_endpoint(req: SaveProfileFieldRequest) -> dict:
    return save_profile_field(req.user_id, req.field, req.value)


@app.get("/budget-snapshot")
def budget_snapshot_endpoint(user_id: str = Query(..., min_length=1)) -> dict:
    """A read on the user's *current* standing — no new purchase — reusing
    affordability_check with purchase_price=0 rather than new math: with
    no new loan, new_emi is 0, so the FOIR verdict reflects existing_emis
    against income exactly, which is what "how's my budget looking" means.

    EMI now prefers the structured loans list (tools/financial_profile.py)
    over the older flat "existing_emis" field when any loans are saved —
    the onboarding flow writes loans, not that field, but a profile saved
    before the onboarding pass still has "existing_emis" and keeps
    working exactly as before. Expenses similarly prefer the itemized
    breakdown's total over the older single "monthly_essential_expenses"
    figure when one exists.
    """
    profile = get_profile(user_id)
    try:
        income = float(profile.get("monthly_income", 0))
    except ValueError:
        raise HTTPException(422, "saved profile has a non-numeric income value")

    if income <= 0:
        return {"profile": profile, "snapshot": None, "note": "no monthly_income saved yet"}

    loans = get_loans(user_id)
    existing_emis = total_monthly_emi(loans) if loans else float(profile.get("existing_emis", 0) or 0)

    expenses = get_expenses(user_id)
    essential = (
        total_monthly_expenses(expenses)
        if expenses
        else profile.get("monthly_essential_expenses")
    )

    snapshot = affordability_check(
        income,
        existing_emis,
        purchase_price=0,
        monthly_essential_expenses=float(essential) if essential is not None else None,
    )
    return {"profile": profile, "loans": loans, "expenses": expenses, "snapshot": snapshot}


@app.get("/profile/loans")
def get_loans_endpoint(user_id: str = Query(..., min_length=1)) -> dict:
    return {"user_id": user_id, "loans": get_loans(user_id)}


class SaveLoansRequest(BaseModel):
    user_id: str
    loans: list[dict]


@app.post("/profile/loans")
def save_loans_endpoint(req: SaveLoansRequest) -> dict:
    save_loans(req.user_id, req.loans)
    return {"user_id": req.user_id, "loans": req.loans, "total_monthly_emi": total_monthly_emi(req.loans)}


@app.get("/profile/expenses")
def get_expenses_endpoint(user_id: str = Query(..., min_length=1)) -> dict:
    expenses = get_expenses(user_id)
    return {"user_id": user_id, "expenses": expenses, "total": total_monthly_expenses(expenses)}


class SaveExpensesRequest(BaseModel):
    user_id: str
    expenses: dict[str, float]


@app.post("/profile/expenses")
def save_expenses_endpoint(req: SaveExpensesRequest) -> dict:
    save_expenses(req.user_id, req.expenses)
    return {
        "user_id": req.user_id,
        "expenses": req.expenses,
        "total": total_monthly_expenses(req.expenses),
    }


@app.get("/personalized-updates")
def personalized_updates_endpoint(user_id: str = Query(..., min_length=1)) -> dict:
    """Real-time news, connected to THIS user's situation — the
    personalization research_agent's plain query lookup never had. Builds
    a query from what's actually in their profile (loans -> rate-related
    news matters; always includes inflation, since that affects everyone's
    expense planning) rather than a generic market query.
    """
    profile = get_profile(user_id)
    loans = get_loans(user_id)

    query_terms = ["India personal finance", "inflation India"]
    if loans:
        query_terms.append("RBI repo rate")
    news = get_market_news(" ".join(query_terms), max_results=5)
    if "error" in news:
        return news

    income = profile.get("monthly_income", "not shared")
    profile_summary = (
        f"Monthly income ₹{income}. "
        f"{len(loans)} active loan(s), total EMI ₹{total_monthly_emi(loans) if loans else 0}/month."
    )
    result = synthesize_personalized_update(profile_summary, news.get("headlines", []))
    result["headlines"] = news.get("headlines", [])
    return result


@app.get("/reminders")
def list_reminders_endpoint(user_id: str = Query(..., min_length=1)) -> dict:
    return {"user_id": user_id, "reminders": get_reminders_for_user(user_id)}


class CreateReminderRequest(BaseModel):
    user_id: str
    message: str
    due_date: str
    recurrence: str = "none"


@app.post("/reminders")
def create_reminder_endpoint(req: CreateReminderRequest) -> dict:
    return create_reminder(req.user_id, req.message, req.due_date, req.recurrence)

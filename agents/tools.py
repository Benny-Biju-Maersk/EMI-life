"""LangChain @tool wrappers around the Phase-1 tool functions.

No math lives here — each wrapper just calls straight into
tools/finance_tools.py and JSON-serializes the result, so Phase 1's tools
(tested in tests/test_tools.py) and Phase 2's specialists share one
implementation. Add a tool to finance_tools.py first, then wrap it here (and
assign it to whichever specialist should own it) — don't reimplement math in
this file.

Docstrings here double as the tool descriptions the model sees when deciding
whether to call a tool, same role tools/schemas.py's "description" fields
play for the Phase-1 agent — kept consistent with that wording on purpose.
"""

from __future__ import annotations

import json

from langchain_core.tools import tool

from tools.finance_tools import (
    affordability_check,
    calculate_emi,
    decode_emi_offer,
    get_stock_quote,
    prepayment_impact,
)
from tools.reminders import create_reminder
from tools.user_profile import get_profile, save_profile_field
from tools.web_research import get_market_news


@tool
def calculate_emi_tool(principal: float, annual_rate_pct: float, tenure_months: int) -> str:
    """Calculate the monthly EMI, total interest, and total payment for a loan
    using the standard reducing-balance formula. Use whenever the user asks
    about EMI amounts, loan costs, or 'what will I pay per month'.

    Args:
        principal: Loan amount in INR.
        annual_rate_pct: Annual interest rate in percent, e.g. 10.5.
        tenure_months: Loan tenure in months.
    """
    return json.dumps(calculate_emi(principal, annual_rate_pct, tenure_months))


@tool
def prepayment_impact_tool(
    principal: float,
    annual_rate_pct: float,
    tenure_months: int,
    months_paid: int,
    lumpsum: float,
) -> str:
    """Estimate how much tenure and interest a one-time loan prepayment saves,
    keeping the EMI constant. Use when the user asks whether to prepay a loan
    or what a lumpsum payment would save them.

    Args:
        principal: Original loan amount in INR.
        annual_rate_pct: Annual interest rate in percent.
        tenure_months: Original loan tenure in months.
        months_paid: EMIs already paid.
        lumpsum: One-time prepayment amount in INR.
    """
    return json.dumps(
        prepayment_impact(principal, annual_rate_pct, tenure_months, months_paid, lumpsum)
    )


@tool
def affordability_check_tool(
    monthly_net_income: float,
    existing_emis: float,
    purchase_price: float,
    down_payment: float = 0,
    annual_rate_pct: float = 15.0,
    tenure_months: int = 12,
    monthly_essential_expenses: float | None = None,
) -> str:
    """Rule-based verdict on whether the user can afford a purchase, using the
    FOIR (fixed obligation to income ratio) rule lenders use. Use whenever the
    user asks 'can I afford X' or 'should I buy X on EMI'. Ask the user for
    their monthly net income and existing EMIs first if you don't know them.

    Args:
        monthly_net_income: Take-home income per month in INR.
        existing_emis: Sum of current monthly EMIs in INR, 0 if none.
        purchase_price: Price of the item being purchased, in INR.
        down_payment: Upfront payment, default 0.
        annual_rate_pct: Expected loan rate, default 15 for consumer loans.
        tenure_months: Planned tenure, default 12.
        monthly_essential_expenses: Rent, food, utilities etc. Optional but
            improves the verdict.
    """
    return json.dumps(
        affordability_check(
            monthly_net_income,
            existing_emis,
            purchase_price,
            down_payment,
            annual_rate_pct,
            tenure_months,
            monthly_essential_expenses,
        )
    )


@tool
def decode_emi_offer_tool(
    item_price: float,
    tenure_months: int,
    processing_fee: float = 0,
    gst_on_fee_pct: float = 18.0,
    forfeited_discount: float = 0,
    stated_interest_pct: float = 0,
) -> str:
    """Decode what a checkout 'no-cost EMI' or BNPL offer actually costs,
    beyond the advertised zero-interest sticker. Use whenever the user is
    facing (or forwards a screenshot of) a checkout EMI offer and asks
    'is this really free', 'should I take this EMI', or similar. If you can
    see or infer a processing fee or a discount/cashback that's only
    available on full payment, pass them in — don't guess a number the
    offer doesn't state; ask the user instead if it matters and isn't shown.

    Args:
        item_price: Sticker price of the item in INR.
        tenure_months: EMI tenure in months.
        processing_fee: Processing/convenience fee before GST, in INR. 0 if none stated.
        gst_on_fee_pct: GST rate applied to the processing fee, default 18.
        forfeited_discount: Instant discount or cashback only available on
            full payment, forfeited by choosing EMI. 0 if none.
        stated_interest_pct: Stated annual interest rate if this isn't
            actually a 'no cost' offer, default 0.
    """
    return json.dumps(
        decode_emi_offer(
            item_price,
            tenure_months,
            processing_fee,
            gst_on_fee_pct,
            forfeited_discount,
            stated_interest_pct,
        )
    )


@tool
def get_stock_quote_tool(symbol: str) -> str:
    """Fetch a recent stock quote (price, day range, 52-week range).
    For NSE stocks append .NS to the symbol (RELIANCE.NS, TCS.NS);
    for BSE append .BO. Use for any question about a current stock price.

    Args:
        symbol: Ticker symbol with exchange suffix, e.g. INFY.NS.
    """
    return json.dumps(get_stock_quote(symbol))


@tool
def save_profile_field_tool(user_id: str, field: str, value: str) -> str:
    """Save or update one durable fact about the user's finances — e.g.
    monthly_income, essential_expenses — so future conversations (even
    brand new ones) can use it without asking again. Use whenever the user
    tells you a fact worth remembering long-term, not just for this
    conversation.

    Args:
        user_id: Stable identifier for the user. Use "default_user" if no
            per-user identity system exists yet (this REPL doesn't have one).
        field: Short snake_case name for the fact, e.g. "monthly_income".
        value: The value, as a string.
    """
    return json.dumps(save_profile_field(user_id, field, value))


@tool
def get_saved_profile_tool(user_id: str) -> str:
    """Fetch every long-term fact already saved about this user (income,
    essential expenses, etc.) from past conversations. Use this BEFORE
    asking the user something you might already know from before.

    Args:
        user_id: Stable identifier for the user. Use "default_user" if no
            per-user identity system exists yet (this REPL doesn't have one).
    """
    return json.dumps(get_profile(user_id))


@tool
def get_market_news_tool(query: str, max_results: int = 5) -> str:
    """Fetch recent real-time news headlines matching a query — a stock
    name, a sector, or an economic topic — from the open web. Use for
    "what's happening with X", "any news on X", or context behind a price
    move. Never invent a headline or recall one from memory; always fetch.

    Args:
        query: Search terms, e.g. "Reliance Industries" or "RBI repo rate".
        max_results: Maximum headlines to return, default 5.
    """
    return json.dumps(get_market_news(query, max_results))


@tool
def create_reminder_tool(
    user_id: str, message: str, due_date: str, recurrence: str = "none"
) -> str:
    """Register a reminder to be delivered LATER, unprompted — not
    something this conversation itself sends. Use when the user asks to
    be reminded about something (an EMI due date, a renewal, a follow-up
    check), never for anything that should happen right now.

    Args:
        user_id: Stable identifier for the user. Use "default_user" if no
            per-user identity system exists yet (this REPL doesn't have
            one) — a real deployment would pass the WhatsApp number
            ("whatsapp:+91...") so scheduler/send_reminders.py can
            actually deliver to them later.
        message: What to remind them of, in plain language.
        due_date: ISO date ("YYYY-MM-DD") the reminder should first fire.
        recurrence: "none" (fires once) or "monthly" (keeps firing on
            roughly the same day each month). Default "none".
    """
    return json.dumps(create_reminder(user_id, message, due_date, recurrence))


CREDIT_DEBT_TOOLS = [calculate_emi_tool, prepayment_impact_tool, affordability_check_tool]
MARKETS_TOOLS = [get_stock_quote_tool]
CHECKOUT_TOOLS = [decode_emi_offer_tool, affordability_check_tool, calculate_emi_tool]
BUDGET_TOOLS = [get_saved_profile_tool, save_profile_field_tool, affordability_check_tool]
RESEARCH_TOOLS = [get_market_news_tool]
REMINDER_TOOLS = [create_reminder_tool, get_saved_profile_tool]

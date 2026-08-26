"""Finance tools the agent can call.

Each tool is a plain Python function plus a JSON schema (in schemas.py).
Keep tools deterministic and side-effect free where possible — it makes
them trivially testable and the agent's behavior predictable.
"""

from __future__ import annotations


def calculate_emi(principal: float, annual_rate_pct: float, tenure_months: int) -> dict:
    """Standard reducing-balance EMI. Returns EMI, total interest, total payment."""
    if principal <= 0 or tenure_months <= 0:
        return {"error": "principal and tenure must be positive"}
    r = (annual_rate_pct / 100) / 12
    if r == 0:
        emi = principal / tenure_months
    else:
        factor = (1 + r) ** tenure_months
        emi = principal * r * factor / (factor - 1)
    total = emi * tenure_months
    return {
        "emi": round(emi, 2),
        "total_payment": round(total, 2),
        "total_interest": round(total - principal, 2),
        "principal": principal,
        "annual_rate_pct": annual_rate_pct,
        "tenure_months": tenure_months,
    }


def prepayment_impact(
    principal: float,
    annual_rate_pct: float,
    tenure_months: int,
    months_paid: int,
    lumpsum: float,
) -> dict:
    """Effect of a one-time prepayment: months saved and interest saved
    (keeping the EMI constant and reducing tenure)."""
    base = calculate_emi(principal, annual_rate_pct, tenure_months)
    if "error" in base:
        return base
    emi = base["emi"]
    r = (annual_rate_pct / 100) / 12

    # Outstanding balance after months_paid
    balance = principal
    for _ in range(months_paid):
        balance = balance * (1 + r) - emi
    if lumpsum >= balance:
        return {"note": "lumpsum clears the loan entirely", "outstanding_before": round(balance, 2)}

    new_balance = balance - lumpsum

    def months_to_close(bal: float) -> int:
        m = 0
        while bal > 0 and m < 1000:
            bal = bal * (1 + r) - emi
            m += 1
        return m

    old_remaining = months_to_close(balance)
    new_remaining = months_to_close(new_balance)
    months_saved = old_remaining - new_remaining
    interest_saved = months_saved * emi - lumpsum * 0  # approx: EMIs avoided minus principal already counted
    # More precise: interest saved = (old_remaining - new_remaining) * emi - 0, since lumpsum reduces principal
    return {
        "outstanding_before_prepayment": round(balance, 2),
        "months_saved": months_saved,
        "approx_interest_saved": round(months_saved * emi - lumpsum, 2),
        "emi_unchanged": emi,
    }


def affordability_check(
    monthly_net_income: float,
    existing_emis: float,
    purchase_price: float,
    down_payment: float = 0,
    annual_rate_pct: float = 15.0,
    tenure_months: int = 12,
    monthly_essential_expenses: float | None = None,
) -> dict:
    """Rule-based affordability verdict using FOIR (fixed obligation to income ratio).

    Lenders in India typically cap total EMIs at 40-50% of net income.
    We use 40% as the 'comfortable' line and 50% as the hard ceiling.
    """
    loan_amount = max(purchase_price - down_payment, 0)
    emi_calc = calculate_emi(loan_amount, annual_rate_pct, tenure_months) if loan_amount > 0 else {"emi": 0}
    new_emi = emi_calc.get("emi", 0)
    total_emis = existing_emis + new_emi
    foir = total_emis / monthly_net_income if monthly_net_income > 0 else 1.0

    if foir <= 0.40:
        verdict = "comfortable"
    elif foir <= 0.50:
        verdict = "stretched"
    else:
        verdict = "not_advisable"

    result = {
        "loan_amount": loan_amount,
        "new_emi": new_emi,
        "total_monthly_emis": round(total_emis, 2),
        "foir_pct": round(foir * 100, 1),
        "verdict": verdict,
        "rule": "FOIR <=40% comfortable, 40-50% stretched, >50% not advisable",
    }
    if monthly_essential_expenses is not None:
        surplus = monthly_net_income - monthly_essential_expenses - total_emis
        result["monthly_surplus_after_emis"] = round(surplus, 2)
        if surplus < 0:
            result["verdict"] = "not_advisable"
            result["note"] = "EMIs exceed disposable income after essential expenses"
    return result


def decode_emi_offer(
    item_price: float,
    tenure_months: int,
    processing_fee: float = 0,
    gst_on_fee_pct: float = 18.0,
    forfeited_discount: float = 0,
    stated_interest_pct: float = 0,
) -> dict:
    """Decode what a checkout 'no-cost EMI' offer actually costs.

    'No-cost EMI' usually means zero *stated* interest (stated_interest_pct=0),
    but the true cost still shows up as a processing fee (+ GST on it) and/or
    an instant-discount or cashback that's only available on full payment and
    silently forfeited by choosing EMI. This makes that hidden cost explicit
    instead of letting "no cost" mean "no cost check performed".

    If stated_interest_pct > 0 (a real-interest EMI, not just a "no cost"
    claim), delegates the amortization math to calculate_emi rather than
    redoing it.
    """
    if item_price <= 0 or tenure_months <= 0:
        return {"error": "item_price and tenure_months must be positive"}

    if stated_interest_pct > 0:
        emi_calc = calculate_emi(item_price, stated_interest_pct, tenure_months)
        if "error" in emi_calc:
            return emi_calc
        base_total = emi_calc["total_payment"]
        monthly_emi = emi_calc["emi"]
    else:
        base_total = item_price
        monthly_emi = round(item_price / tenure_months, 2)

    fee_with_gst = round(processing_fee * (1 + gst_on_fee_pct / 100), 2)
    hidden_cost = round(fee_with_gst + forfeited_discount, 2)
    effective_total_cost = round(base_total + hidden_cost, 2)

    verdict = "actually no-cost" if hidden_cost == 0 else "has hidden cost"

    return {
        "monthly_emi": monthly_emi,
        "sticker_total": base_total,
        "processing_fee_with_gst": fee_with_gst,
        "forfeited_discount": forfeited_discount,
        "hidden_cost": hidden_cost,
        "effective_total_cost": effective_total_cost,
        "extra_cost_vs_paying_in_full": hidden_cost,
        "verdict": verdict,
    }


def get_stock_quote(symbol: str) -> dict:
    """Fetch a recent quote via yfinance. NSE symbols need a .NS suffix
    (e.g. RELIANCE.NS), BSE symbols .BO. Free data, ~15 min delayed —
    fine for learning; swap for Kite Connect in production."""
    try:
        import yfinance as yf
    except ImportError:
        return {"error": "yfinance not installed. Run: pip install yfinance"}
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        return {
            "symbol": symbol,
            "last_price": round(float(info.last_price), 2),
            "day_high": round(float(info.day_high), 2),
            "day_low": round(float(info.day_low), 2),
            "year_high": round(float(info.year_high), 2),
            "year_low": round(float(info.year_low), 2),
            "currency": info.currency,
        }
    except Exception as e:
        return {"error": f"could not fetch quote for {symbol}: {e}"}


# Registry the agent loop uses to dispatch tool calls by name
TOOL_FUNCTIONS = {
    "calculate_emi": calculate_emi,
    "prepayment_impact": prepayment_impact,
    "affordability_check": affordability_check,
    "decode_emi_offer": decode_emi_offer,
    "get_stock_quote": get_stock_quote,
}

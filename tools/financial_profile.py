"""Structured financial-profile data, built on top of
tools/user_profile.py's flat field/value store rather than a new storage
mechanism — a list of loans or a breakdown of expense categories doesn't
fit one scalar value, so this module stores each as JSON under one field
name and hands back real Python lists/dicts. Callers (the onboarding API,
dashboard widgets) never touch raw JSON strings.

This is a shape convention on top of tier-3 memory (see
docs/multi-agent-patterns.md #2), not a different memory tier — same
`data/profiles.db`, same `save_profile_field`/`get_profile` underneath.

Added for the onboarding-questionnaire pass: rather than the single lump
`existing_emis` figure the Budget specialist/Budget Snapshot widget used
before, a user's actual loans are now individually named and dated, and
`total_monthly_emi` derives the aggregate by delegating to
`calculate_emi` — never re-deriving amortization math, same pattern
`decode_emi_offer` already established.
"""

from __future__ import annotations

import json

from tools.finance_tools import calculate_emi
from tools.user_profile import get_profile, save_profile_field

LOANS_FIELD = "loans"
EXPENSES_FIELD = "expenses_by_category"


def save_loans(user_id: str, loans: list[dict]) -> dict:
    """loans: list of {name, principal, annual_rate_pct, tenure_months,
    months_paid}. Replaces the full list — callers read, modify, and
    re-save the whole thing, same as an onboarding form submitting
    everything at once."""
    return save_profile_field(user_id, LOANS_FIELD, json.dumps(loans))


def get_loans(user_id: str) -> list[dict]:
    """[] for a user with no saved loans — never an error; "no loans" is
    a perfectly normal, common state, not a missing-data problem."""
    raw = get_profile(user_id).get(LOANS_FIELD)
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def total_monthly_emi(loans: list[dict]) -> float:
    """Sum of every loan's EMI. Delegates to calculate_emi for each —
    never re-derives reducing-balance math here."""
    total = 0.0
    for loan in loans:
        emi_calc = calculate_emi(
            loan.get("principal", 0),
            loan.get("annual_rate_pct", 0),
            loan.get("tenure_months", 1),
        )
        total += emi_calc.get("emi", 0)
    return round(total, 2)


def save_expenses(user_id: str, expenses: dict[str, float]) -> dict:
    """expenses: category name -> monthly amount, e.g.
    {"rent": 20000, "groceries": 8000}. Replaces the full breakdown."""
    return save_profile_field(user_id, EXPENSES_FIELD, json.dumps(expenses))


def get_expenses(user_id: str) -> dict:
    raw = get_profile(user_id).get(EXPENSES_FIELD)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def total_monthly_expenses(expenses: dict) -> float:
    return round(sum(float(v) for v in expenses.values()), 2)

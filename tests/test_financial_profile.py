"""Deterministic tests for tools/financial_profile.py. Same DB-isolation
pattern as test_user_profile.py: financial_profile.py stores through
tools/user_profile.py's save_profile_field, so patching THAT module's
DB_PATH is what isolates these tests, not financial_profile.py's own
(it has none — it has no DB_PATH of its own, it delegates entirely).
"""

from __future__ import annotations

import tools.financial_profile as financial_profile
import tools.user_profile as user_profile


def test_no_loans_saved_returns_empty_list(tmp_path, monkeypatch):
    monkeypatch.setattr(user_profile, "DB_PATH", tmp_path / "profiles.db")
    assert financial_profile.get_loans("default_user") == []


def test_save_and_get_loans_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(user_profile, "DB_PATH", tmp_path / "profiles.db")
    loans = [
        {"name": "Car loan", "principal": 500000, "annual_rate_pct": 9.5, "tenure_months": 60, "months_paid": 12},
        {"name": "Phone EMI", "principal": 30000, "annual_rate_pct": 0, "tenure_months": 6, "months_paid": 2},
    ]
    financial_profile.save_loans("default_user", loans)
    assert financial_profile.get_loans("default_user") == loans


def test_total_monthly_emi_sums_across_loans():
    loans = [
        {"principal": 1_000_000, "annual_rate_pct": 10, "tenure_months": 60},
        {"principal": 120_000, "annual_rate_pct": 0, "tenure_months": 12},
    ]
    # 1,000,000 @ 10% / 60mo has a known EMI (see test_tools.py's pinned
    # value at a different tenure); just check it matches calculate_emi
    # directly rather than re-deriving/pinning a second value here.
    from tools.finance_tools import calculate_emi

    expected = round(
        calculate_emi(1_000_000, 10, 60)["emi"] + calculate_emi(120_000, 0, 12)["emi"], 2
    )
    assert financial_profile.total_monthly_emi(loans) == expected


def test_total_monthly_emi_of_no_loans_is_zero():
    assert financial_profile.total_monthly_emi([]) == 0.0


def test_expenses_roundtrip_and_total(tmp_path, monkeypatch):
    monkeypatch.setattr(user_profile, "DB_PATH", tmp_path / "profiles.db")
    expenses = {"rent": 20000, "groceries": 8000, "utilities": 3000}
    financial_profile.save_expenses("default_user", expenses)
    assert financial_profile.get_expenses("default_user") == expenses
    assert financial_profile.total_monthly_expenses(expenses) == 31000.0


def test_no_expenses_saved_returns_empty_dict(tmp_path, monkeypatch):
    monkeypatch.setattr(user_profile, "DB_PATH", tmp_path / "profiles.db")
    assert financial_profile.get_expenses("default_user") == {}

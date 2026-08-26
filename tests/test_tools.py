"""Deterministic tool tests — run with: python -m pytest tests/ -q"""
from tools.finance_tools import calculate_emi, affordability_check, decode_emi_offer


def test_emi_known_value():
    r = calculate_emi(1_000_000, 10, 60)
    assert abs(r["emi"] - 21247.04) < 1


def test_emi_zero_rate():
    r = calculate_emi(120_000, 0, 12)
    assert r["emi"] == 10_000


def test_affordability_comfortable():
    r = affordability_check(100_000, 10_000, 60_000, tenure_months=12)
    assert r["verdict"] == "comfortable"


def test_affordability_over_ceiling():
    r = affordability_check(50_000, 24_000, 500_000, tenure_months=12)
    assert r["verdict"] == "not_advisable"


def test_decode_emi_offer_hidden_processing_fee():
    # ₹40,000 item, 12mo "no cost" EMI, ₹499 processing fee + 18% GST on it.
    r = decode_emi_offer(40_000, 12, processing_fee=499, gst_on_fee_pct=18)
    assert r["processing_fee_with_gst"] == 588.82
    assert r["hidden_cost"] == 588.82
    assert r["effective_total_cost"] == 40_588.82
    assert r["verdict"] == "has hidden cost"


def test_decode_emi_offer_genuinely_no_cost():
    r = decode_emi_offer(40_000, 12)
    assert r["hidden_cost"] == 0
    assert r["verdict"] == "actually no-cost"
    assert r["monthly_emi"] == round(40_000 / 12, 2)


def test_decode_emi_offer_forfeited_discount():
    # No processing fee, but a ₹2,000 instant discount only on full payment.
    r = decode_emi_offer(40_000, 12, forfeited_discount=2_000)
    assert r["hidden_cost"] == 2_000
    assert r["effective_total_cost"] == 42_000
    assert r["verdict"] == "has hidden cost"

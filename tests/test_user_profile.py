"""Deterministic tests for tier-3 (long-term profile) memory — no network,
no API key needed, same spirit as test_tools.py. Each test points DB_PATH
at a fresh temp file so runs never touch or pollute the real
data/profiles.db.
"""

from __future__ import annotations

import tools.user_profile as user_profile


def test_get_profile_empty_for_unknown_user(tmp_path, monkeypatch):
    monkeypatch.setattr(user_profile, "DB_PATH", tmp_path / "profiles.db")
    assert user_profile.get_profile("someone_new") == {}


def test_save_then_get_roundtrips(tmp_path, monkeypatch):
    monkeypatch.setattr(user_profile, "DB_PATH", tmp_path / "profiles.db")
    user_profile.save_profile_field("default_user", "monthly_income", "90000")
    assert user_profile.get_profile("default_user") == {"monthly_income": "90000"}


def test_save_overwrites_existing_field(tmp_path, monkeypatch):
    monkeypatch.setattr(user_profile, "DB_PATH", tmp_path / "profiles.db")
    user_profile.save_profile_field("default_user", "monthly_income", "90000")
    user_profile.save_profile_field("default_user", "monthly_income", "95000")
    assert user_profile.get_profile("default_user") == {"monthly_income": "95000"}


def test_profiles_are_isolated_per_user(tmp_path, monkeypatch):
    monkeypatch.setattr(user_profile, "DB_PATH", tmp_path / "profiles.db")
    user_profile.save_profile_field("user_a", "monthly_income", "50000")
    user_profile.save_profile_field("user_b", "monthly_income", "200000")
    assert user_profile.get_profile("user_a") == {"monthly_income": "50000"}
    assert user_profile.get_profile("user_b") == {"monthly_income": "200000"}


def test_multiple_fields_accumulate(tmp_path, monkeypatch):
    monkeypatch.setattr(user_profile, "DB_PATH", tmp_path / "profiles.db")
    user_profile.save_profile_field("default_user", "monthly_income", "90000")
    user_profile.save_profile_field("default_user", "monthly_essential_expenses", "30000")
    assert user_profile.get_profile("default_user") == {
        "monthly_income": "90000",
        "monthly_essential_expenses": "30000",
    }

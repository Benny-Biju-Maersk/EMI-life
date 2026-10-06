"""Tests for agents/council.py's debate/consensus pattern.

The structural tests never touch the network. The live test runs the full
panel + chairman flow for real and is skipped automatically when no
GROQ_API_KEY is configured — same spirit as tests/test_agents.py.
"""

from __future__ import annotations

import asyncio
import os

import pytest
from dotenv import load_dotenv

load_dotenv()

from agents.council import PANELIST_MODELS, _format_question, run_council  # noqa: E402


def test_panelists_are_genuinely_distinct_models():
    # The whole point of a council is independence — catch a future edit
    # that accidentally collapses this to one model asked three times.
    assert len(PANELIST_MODELS) >= 3
    assert len(set(PANELIST_MODELS)) == len(PANELIST_MODELS)


def test_format_question_without_context_is_unchanged():
    assert _format_question("should I take this loan?", None) == "should I take this loan?"


def test_format_question_with_context_includes_it():
    formatted = _format_question("should I take this loan?", {"monthly_net_income": 60000})
    assert "should I take this loan?" in formatted
    assert "60000" in formatted


@pytest.mark.skipif(not os.environ.get("GROQ_API_KEY"), reason="no GROQ_API_KEY configured")
def test_live_council_produces_synthesis_from_multiple_opinions():
    result = asyncio.run(
        run_council(
            "I earn 60000 a month with no existing EMIs. Should I buy a "
            "45000 phone on a 6-month no-cost EMI with a 999 processing fee?"
        )
    )
    assert "error" not in result
    assert len(result["opinions"]) == len(PANELIST_MODELS)
    assert result["synthesis"]

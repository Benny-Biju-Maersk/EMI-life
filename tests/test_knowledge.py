"""tools/knowledge.py's RAG retrieval — fully deterministic, no network, no
API key: TF-IDF over the static `knowledge/*.md` files."""

from __future__ import annotations

from tools.knowledge import answer_from_knowledge_base


def test_finds_foir_doc_for_affordability_question():
    result = answer_from_knowledge_base("what FOIR percentage is considered safe")
    assert "error" not in result
    sources = [r["source"] for r in result["results"]]
    assert "foir-affordability.md" in sources


def test_finds_no_cost_emi_doc_for_hidden_fee_question():
    result = answer_from_knowledge_base("does no cost EMI have a hidden processing fee")
    sources = [r["source"] for r in result["results"]]
    assert "no-cost-emi-hidden-costs.md" in sources


def test_finds_sebi_doc_for_investment_advice_question():
    result = answer_from_knowledge_base("can you tell me which stock to buy")
    sources = [r["source"] for r in result["results"]]
    assert "sebi-ria-line.md" in sources


def test_empty_query_is_an_error():
    result = answer_from_knowledge_base("")
    assert "error" in result


def test_nonsense_query_can_return_no_results():
    # Not asserting emptiness (TF-IDF may still find a weak match) — just
    # that a low-signal query never raises and always returns the shape.
    result = answer_from_knowledge_base("xyzzy quux plugh")
    assert "results" in result

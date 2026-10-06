"""RAG over `knowledge/*.md` — the one genuinely new capability class this
adds: everything else in `tools/` either computes (finance_tools.py), reads
a private per-user store (user_profile.py, reminders.py), or fetches live
web content (web_research.py). This reads a small, curated, FinBuddy-owned
set of facts (FOIR rules, what "no-cost EMI" hides, credit score factors,
the SEBI-RIA line) so an agent can *cite* a stable answer instead of
re-deriving or hallucinating one each time, and instead of spending a live
web search on something that doesn't change day to day.

Retrieval is deliberately TF-IDF + cosine similarity
(`sklearn.feature_extraction.text.TfidfVectorizer`), not a real embedding
model — no model download, fully in-process, and the mechanics (vectorize
query, compare against pre-vectorized chunks, return the closest ones) are
easy to read start to finish, which matters more than retrieval quality
for a handful of short documents in a learning project. Swapping in real
embeddings later only means changing `_vectorize`/`_similarity` — the
chunking and the public `answer_from_knowledge_base` signature don't need
to change.

The index is built once per process, at import time, from whatever's in
`knowledge/*.md` — there's no separate "build the index" step to remember
to run, and no persisted index file to go stale against the docs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"


@dataclass
class Chunk:
    source: str  # e.g. "foir-affordability.md"
    heading: str  # the "## ..." (or "# ...") heading this chunk falls under
    text: str


def _load_chunks(knowledge_dir: Path = KNOWLEDGE_DIR) -> list[Chunk]:
    """Split each markdown file on its headings — one chunk per section,
    small enough that a single chunk is usually a complete, self-contained
    answer rather than a fragment needing the whole doc for context."""
    chunks: list[Chunk] = []
    for path in sorted(knowledge_dir.glob("*.md")):
        heading = path.stem
        lines: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("#"):
                if lines:
                    chunks.append(Chunk(path.name, heading, "\n".join(lines).strip()))
                heading = line.lstrip("#").strip()
                lines = [line]
            else:
                lines.append(line)
        if lines:
            chunks.append(Chunk(path.name, heading, "\n".join(lines).strip()))
    return chunks


class _Index:
    """Lazily built on first use, not at import time — importing this
    module shouldn't fail just because `knowledge/` is briefly empty (e.g.
    mid-edit) or scikit-learn is slow to import in a cold process; tests
    that don't touch retrieval never pay for it."""

    def __init__(self) -> None:
        self._chunks: list[Chunk] | None = None
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None

    def _ensure_built(self) -> None:
        if self._chunks is not None:
            return
        self._chunks = _load_chunks()
        self._vectorizer = TfidfVectorizer(stop_words="english")
        if self._chunks:
            self._matrix = self._vectorizer.fit_transform([c.text for c in self._chunks])

    def search(self, query: str, top_k: int) -> list[tuple[Chunk, float]]:
        self._ensure_built()
        if not self._chunks:
            return []
        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix)[0]
        ranked = sorted(zip(self._chunks, scores), key=lambda pair: pair[1], reverse=True)
        return [pair for pair in ranked[:top_k] if pair[1] > 0]


_INDEX = _Index()


def answer_from_knowledge_base(query: str, top_k: int = 3) -> dict:
    """Retrieve the `top_k` most relevant chunks from `knowledge/*.md` for
    `query`. Returns each chunk's source file, heading, text, and
    similarity score (0-1, TF-IDF cosine — not a calibrated confidence,
    just a ranking signal) so a caller can decide whether the top result is
    actually relevant enough to use rather than always trusting rank 1.
    Empty `results` (not an error) means nothing in the knowledge base is
    a good match — the caller should fall back to live search/reasoning,
    not report a wrong answer confidently.
    """
    if not query or not query.strip():
        return {"error": "query must not be empty"}
    results = _INDEX.search(query, top_k)
    return {
        "query": query,
        "results": [
            {"source": c.source, "heading": c.heading, "text": c.text, "score": round(float(s), 3)}
            for c, s in results
        ],
    }

"""Live web research: fetches real-time information from the open web —
a genuinely different capability class from everything else in tools/.
calculate_emi is pure math; get_saved_profile reads a local, private
sqlite file (see docs/multi-agent-patterns.md's memory tiers). This module
reaches outside the process entirely, over the network, to a source
FinBuddy doesn't control.

Added for the multi-agent learning track (see docs/multi-agent-patterns.md)
and as groundwork toward the informational stock analyzer scoped — not yet
built — in docs/product-brief.md.

Deliberately uses Google News' public RSS feed rather than scraping any
specific finance site's HTML: RSS is meant for third-party consumption (no
ToS ambiguity the way scraping a page that offers no such feed would have),
and is far more robust — a site redesign doesn't silently break this the
way an HTML scraper would. "Web scraping" in spirit (live, unstructured
web content parsed into structured data) without the legal/reliability
landmines of parsing someone's HTML directly.

Informational only, matching the SEBI line already decided for any
markets-related feature in this repo: this returns headlines and links,
never a sentiment score, a buy/sell signal, or a recommendation.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

_FEED_URL = "https://news.google.com/rss/search"


def get_market_news(query: str, max_results: int = 5) -> dict:
    """Fetch recent news headlines matching a query — a stock name, a
    sector, an economic topic. Returns title/link/published/source per
    headline. No sentiment, no recommendation: just what's being reported.
    """
    if not query or not query.strip():
        return {"error": "query must not be empty"}
    if max_results <= 0:
        return {"error": "max_results must be positive"}

    params = {"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}
    try:
        resp = httpx.get(_FEED_URL, params=params, timeout=10.0, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        return {"error": f"could not fetch news for {query!r}: {e}"}

    try:
        root = ET.fromstring(resp.text)
        items = root.findall("./channel/item")[:max_results]
    except ET.ParseError as e:
        return {"error": f"could not parse news feed: {e}"}

    headlines = [
        {
            "title": (item.findtext("title") or "").strip(),
            "link": (item.findtext("link") or "").strip(),
            "published": (item.findtext("pubDate") or "").strip(),
            "source": (item.findtext("source") or "").strip(),
        }
        for item in items
    ]
    return {"query": query, "headline_count": len(headlines), "headlines": headlines}

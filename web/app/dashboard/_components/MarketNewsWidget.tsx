"use client";

import { useState } from "react";
import { API_URL, Card, TextField } from "./shared";

type Headline = {
  title: string;
  link: string;
  published: string;
  source: string;
};

type NewsResult = {
  headlines?: Headline[];
  error?: string;
};

export function MarketNewsWidget() {
  const [query, setQuery] = useState("RBI repo rate");
  const [result, setResult] = useState<NewsResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function fetchNews() {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_URL}/market-news?query=${encodeURIComponent(query)}&max_results=4`
      );
      setResult(await res.json());
    } catch {
      setResult({ error: "Couldn't reach the API" });
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card title="Market News">
      <p className="text-xs text-muted-foreground">
        Headlines only — never a buy/sell signal.
      </p>
      <div className="mt-2 flex gap-2 text-sm">
        <div className="flex-1">
          <TextField label="Search" value={query} onChange={setQuery} />
        </div>
        <button
          type="button"
          onClick={fetchNews}
          disabled={loading}
          className="mt-5 h-fit rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground transition hover:bg-primary/90 disabled:opacity-50"
        >
          {loading ? "…" : "Search"}
        </button>
      </div>
      {result?.error && <p className="mt-3 text-sm text-destructive">{result.error}</p>}
      {result?.headlines && (
        <ul className="mt-3 space-y-2 text-sm">
          {result.headlines.map((h) => (
            <li key={h.link} className="border-t border-border pt-2 first:border-t-0 first:pt-0">
              <a
                href={h.link}
                target="_blank"
                rel="noopener noreferrer"
                className="text-foreground hover:underline"
              >
                {h.title}
              </a>
              <p className="text-xs text-muted-foreground">{h.source}</p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

"use client";

import { useState } from "react";
import { API_URL, Card, Row, TextField } from "./shared";

type QuoteResult = {
  symbol?: string;
  last_price?: number;
  day_high?: number;
  day_low?: number;
  currency?: string;
  error?: string;
};

export function StockQuoteWidget() {
  const [symbol, setSymbol] = useState("RELIANCE.NS");
  const [result, setResult] = useState<QuoteResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function fetchQuote() {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/stock-quote?symbol=${encodeURIComponent(symbol)}`);
      setResult(await res.json());
    } catch {
      setResult({ error: "Couldn't reach the API" });
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card title="Stock Quote">
      <p className="text-xs text-muted-foreground">
        Informational only — not investment advice. NSE symbols need a
        &ldquo;.NS&rdquo; suffix.
      </p>
      <div className="mt-2 flex gap-2 text-sm">
        <div className="flex-1">
          <TextField label="Symbol" value={symbol} onChange={setSymbol} />
        </div>
        <button
          type="button"
          onClick={fetchQuote}
          disabled={loading}
          className="mt-5 h-fit rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground transition hover:bg-primary/90 disabled:opacity-50"
        >
          {loading ? "…" : "Get quote"}
        </button>
      </div>
      {result &&
        (result.error ? (
          <p className="mt-3 text-sm text-destructive">{result.error}</p>
        ) : (
          <dl className="mt-3 space-y-1 text-sm">
            <Row label="Last price" value={result.last_price} />
            <Row label="Day high" value={result.day_high} />
            <Row label="Day low" value={result.day_low} />
          </dl>
        ))}
    </Card>
  );
}

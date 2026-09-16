"use client";

import { useEffect, useState } from "react";
import { Card } from "./shared";

type Headline = {
  title: string;
  link: string;
  source: string;
};

type UpdatesResponse = {
  note?: string;
  headlines?: Headline[];
  error?: string;
};

export function PersonalizedUpdatesWidget() {
  const [data, setData] = useState<UpdatesResponse | null>(null);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    fetch("/api/personalized-updates")
      .then((r) => r.json())
      .then(setData)
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  return (
    <Card title="What's Happening — For You">
      <p className="text-xs text-muted-foreground">
        Real-time news, connected to your saved loans and income — never a
        buy/sell signal.
      </p>
      {loading ? (
        <p className="mt-3 text-sm text-muted-foreground">Checking the news…</p>
      ) : data?.error ? (
        <p className="mt-3 text-sm text-destructive">{data.error}</p>
      ) : (
        <>
          {data?.note && <p className="mt-3 text-sm leading-relaxed">{data.note}</p>}
          {data?.headlines && data.headlines.length > 0 && (
            <ul className="mt-3 space-y-1 text-xs text-muted-foreground">
              {data.headlines.slice(0, 3).map((h) => (
                <li key={h.link}>
                  <a href={h.link} target="_blank" rel="noopener noreferrer" className="hover:underline">
                    {h.title}
                  </a>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
      <button
        type="button"
        onClick={load}
        className="mt-3 text-xs text-muted-foreground underline hover:text-foreground"
      >
        Refresh
      </button>
    </Card>
  );
}

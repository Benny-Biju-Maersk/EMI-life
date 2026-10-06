"use client";

import { useState, type FormEvent } from "react";
import { Card } from "./shared";

type Opinion = {
  model: string;
  answer: string | null;
  error: string | null;
};

type CouncilResponse = {
  question?: string;
  opinions?: Opinion[];
  synthesis?: string;
  error?: string;
};

// Short, readable labels for the actual Groq model ids — see
// agents/council.py's docstring for why these three specifically (the
// only text-capable models this Groq account has, verified live).
const MODEL_LABELS: Record<string, string> = {
  "openai/gpt-oss-120b": "GPT-OSS 120B",
  "openai/gpt-oss-20b": "GPT-OSS 20B",
  "qwen/qwen3.8-27b": "Qwen3 27B",
};

export function CouncilWidget() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<CouncilResponse | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch("/api/council", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      setResult(await res.json());
    } catch {
      setResult({ error: "Couldn't reach the council — try again in a moment." });
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card title="Ask the Council">
      <p className="text-xs text-muted-foreground">
        For a real judgment call ("should I take this loan"), not routine
        math: three independent models each answer on their own, then a
        chairman model synthesizes — and says where they actually
        disagreed, rather than hiding it.
      </p>

      <form onSubmit={handleSubmit} className="mt-3 flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Should I take this 6-month no-cost EMI?"
          className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20"
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="shrink-0 rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground transition hover:bg-primary/90 disabled:opacity-50"
        >
          {loading ? "Asking…" : "Ask"}
        </button>
      </form>

      {result?.error && <p className="mt-3 text-sm text-destructive">{result.error}</p>}

      {result?.synthesis && (
        <div className="mt-4 space-y-3 text-sm">
          <div className="whitespace-pre-wrap leading-relaxed">{result.synthesis}</div>

          <details className="rounded-md border border-border/60 p-2">
            <summary className="cursor-pointer text-xs text-muted-foreground">
              See each panelist&apos;s independent answer
            </summary>
            <div className="mt-2 space-y-3">
              {result.opinions?.map((o) => (
                <div key={o.model}>
                  <p className="text-xs font-medium text-muted-foreground">
                    {MODEL_LABELS[o.model] ?? o.model}
                  </p>
                  <p className="whitespace-pre-wrap text-xs leading-relaxed">
                    {o.answer ?? `(no answer — ${o.error})`}
                  </p>
                </div>
              ))}
            </div>
          </details>
        </div>
      )}
    </Card>
  );
}

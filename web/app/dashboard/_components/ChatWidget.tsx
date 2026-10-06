"use client";

import { useState, type FormEvent } from "react";
import { Card } from "./shared";

type Turn = {
  role: "user" | "assistant";
  content: string;
  handledBy?: string | null;
};

// Matches agents/orchestrator.py's agents=[...] list — short labels for the
// transparency line under each reply ("answered by: ...").
const SPECIALIST_LABELS: Record<string, string> = {
  credit_debt_agent: "Credit/Debt specialist",
  markets_agent: "Markets specialist",
  budget_agent: "Budget specialist",
  research_agent: "Research specialist",
  reminder_agent: "Reminder specialist",
  council_agent: "The Council",
};

export function ChatWidget() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const text = message.trim();
    if (!text) return;
    setMessage("");
    setTurns((t) => [...t, { role: "user", content: text }]);
    setLoading(true);
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();
      setTurns((t) => [
        ...t,
        {
          role: "assistant",
          content: data.reply ?? data.error ?? "Something went wrong.",
          handledBy: data.handled_by ?? null,
        },
      ]);
    } catch {
      setTurns((t) => [
        ...t,
        { role: "assistant", content: "Couldn't reach FinBuddy — try again in a moment." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card title="Ask FinBuddy Anything">
      <p className="text-xs text-muted-foreground">
        Routed automatically to whichever specialist fits — remembers this
        conversation across your visits to this dashboard.
      </p>

      <div className="mt-3 max-h-64 space-y-3 overflow-y-auto text-sm">
        {turns.length === 0 && !loading && (
          <p className="text-muted-foreground/70">
            Try: &ldquo;What&apos;s my EMI on a 5 lakh loan at 10% for 24
            months?&rdquo;
          </p>
        )}
        {turns.map((t, i) => (
          <div key={i} className={t.role === "user" ? "text-right" : "text-left"}>
            <p
              className={
                t.role === "user"
                  ? "inline-block rounded-lg bg-primary px-3 py-1.5 text-primary-foreground"
                  : "inline-block rounded-lg bg-muted px-3 py-1.5"
              }
            >
              {t.content}
            </p>
            {t.handledBy && (
              <p className="mt-0.5 text-xs text-muted-foreground/70">
                — {SPECIALIST_LABELS[t.handledBy] ?? t.handledBy}
              </p>
            )}
          </div>
        ))}
        {loading && <p className="text-muted-foreground/70">Thinking…</p>}
      </div>

      <form onSubmit={handleSubmit} className="mt-3 flex gap-2">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Ask about EMIs, budgets, stocks, reminders…"
          className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20"
        />
        <button
          type="submit"
          disabled={loading || !message.trim()}
          className="shrink-0 rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground transition hover:bg-primary/90 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </Card>
  );
}

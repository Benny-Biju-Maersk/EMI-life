"use client";

import { useEffect, useState } from "react";
import { Card, NumberField, TextField } from "./shared";

type Expenses = Record<string, number>;

export function ExpensesWidget() {
  const [expenses, setExpenses] = useState<Expenses>({});
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [category, setCategory] = useState("");
  const [amount, setAmount] = useState("");

  function load() {
    setLoading(true);
    fetch("/api/profile/expenses")
      .then((r) => r.json())
      .then((data) => {
        setExpenses(data.expenses ?? {});
        setTotal(data.total ?? 0);
      })
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function persist(next: Expenses) {
    setSaving(true);
    try {
      const res = await fetch("/api/profile/expenses", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ expenses: next }),
      });
      const data = await res.json();
      setExpenses(data.expenses ?? next);
      setTotal(data.total ?? 0);
    } finally {
      setSaving(false);
    }
  }

  async function addCategory() {
    if (!category || !amount) return;
    await persist({ ...expenses, [category]: Number(amount) });
    setCategory("");
    setAmount("");
  }

  async function removeCategory(key: string) {
    const next = { ...expenses };
    delete next[key];
    await persist(next);
  }

  const entries = Object.entries(expenses);
  const max = Math.max(1, ...entries.map(([, v]) => v));

  return (
    <Card title="Savings & Expenditure Analysis">
      <p className="text-xs text-muted-foreground">
        Where your income actually goes each month, by category.
      </p>

      {loading ? (
        <p className="mt-3 text-sm text-muted-foreground">Loading…</p>
      ) : (
        <>
          {entries.length > 0 && (
            <div className="mt-3 space-y-2 text-sm">
              {entries.map(([key, value]) => (
                <div key={key}>
                  <div className="flex justify-between">
                    <span className="capitalize">{key}</span>
                    <span className="flex items-center gap-2">
                      ₹{value.toLocaleString("en-IN")}
                      <button
                        type="button"
                        onClick={() => removeCategory(key)}
                        className="text-xs text-destructive hover:underline"
                      >
                        ✕
                      </button>
                    </span>
                  </div>
                  <div className="mt-1 h-1.5 w-full rounded-full bg-border">
                    <div
                      className="h-1.5 rounded-full bg-primary"
                      style={{ width: `${(value / max) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
              <div className="flex justify-between border-t border-border pt-2 font-medium">
                <span>Total</span>
                <span>₹{total.toLocaleString("en-IN")}</span>
              </div>
            </div>
          )}

          <div className="mt-4 border-t border-border pt-3">
            <p className="mb-2 text-xs font-medium text-muted-foreground">Add a category</p>
            <div className="flex items-end gap-2 text-sm">
              <div className="flex-1">
                <TextField label="Category" value={category} onChange={setCategory} placeholder="rent" />
              </div>
              <div className="flex-1">
                <NumberField label="Monthly amount (₹)" value={amount} onChange={setAmount} />
              </div>
            </div>
            <button
              type="button"
              onClick={addCategory}
              disabled={saving}
              className="mt-2 w-full rounded-md bg-primary py-1.5 text-sm text-primary-foreground transition hover:bg-primary/90 disabled:opacity-50"
            >
              {saving ? "Saving…" : "Add category"}
            </button>
          </div>
        </>
      )}
    </Card>
  );
}

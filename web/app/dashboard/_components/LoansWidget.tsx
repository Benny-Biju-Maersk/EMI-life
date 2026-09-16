"use client";

import { useEffect, useState } from "react";
import { Card, NumberField, Row, TextField } from "./shared";

type Loan = {
  name: string;
  principal: number;
  annual_rate_pct: number;
  tenure_months: number;
  months_paid: number;
};

export function LoansWidget() {
  const [loans, setLoans] = useState<Loan[]>([]);
  const [totalEmi, setTotalEmi] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [name, setName] = useState("");
  const [principal, setPrincipal] = useState("");
  const [rate, setRate] = useState("");
  const [tenure, setTenure] = useState("");
  const [monthsPaid, setMonthsPaid] = useState("0");

  function load() {
    setLoading(true);
    fetch("/api/profile/loans")
      .then((r) => r.json())
      .then((data) => setLoans(data.loans ?? []))
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function persist(next: Loan[]) {
    setSaving(true);
    try {
      const res = await fetch("/api/profile/loans", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ loans: next }),
      });
      const data = await res.json();
      setLoans(data.loans ?? next);
      setTotalEmi(data.total_monthly_emi ?? null);
    } finally {
      setSaving(false);
    }
  }

  async function addLoan() {
    if (!name || !principal || !tenure) return;
    const loan: Loan = {
      name,
      principal: Number(principal),
      annual_rate_pct: Number(rate || 0),
      tenure_months: Number(tenure),
      months_paid: Number(monthsPaid || 0),
    };
    await persist([...loans, loan]);
    setName("");
    setPrincipal("");
    setRate("");
    setTenure("");
    setMonthsPaid("0");
  }

  async function removeLoan(index: number) {
    await persist(loans.filter((_, i) => i !== index));
  }

  return (
    <Card title="My Loans">
      <p className="text-xs text-muted-foreground">
        Every loan you&apos;re carrying — Budget Snapshot&apos;s EMI total
        comes from this list, not a single guessed number.
      </p>

      {loading ? (
        <p className="mt-3 text-sm text-muted-foreground">Loading…</p>
      ) : (
        <>
          {loans.length > 0 && (
            <ul className="mt-3 space-y-2 text-sm">
              {loans.map((loan, i) => (
                <li
                  key={`${loan.name}-${i}`}
                  className="flex items-center justify-between border-t border-border pt-2 first:border-t-0 first:pt-0"
                >
                  <div>
                    <p className="font-medium">{loan.name}</p>
                    <p className="text-xs text-muted-foreground">
                      ₹{loan.principal.toLocaleString("en-IN")} · {loan.annual_rate_pct}% ·{" "}
                      {loan.tenure_months}mo
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeLoan(i)}
                    className="text-xs text-destructive hover:underline"
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          )}
          {totalEmi !== null && (
            <div className="mt-3">
              <Row label="Total monthly EMI" value={totalEmi} />
            </div>
          )}

          <div className="mt-4 border-t border-border pt-3">
            <p className="mb-2 text-xs font-medium text-muted-foreground">Add a loan</p>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <TextField label="Name" value={name} onChange={setName} placeholder="Car loan" />
              <NumberField label="Principal (₹)" value={principal} onChange={setPrincipal} />
              <NumberField label="Rate (%/yr)" value={rate} onChange={setRate} />
              <NumberField label="Tenure (months)" value={tenure} onChange={setTenure} />
              <NumberField label="Months already paid" value={monthsPaid} onChange={setMonthsPaid} />
            </div>
            <button
              type="button"
              onClick={addLoan}
              disabled={saving}
              className="mt-2 w-full rounded-md bg-primary py-1.5 text-sm text-primary-foreground transition hover:bg-primary/90 disabled:opacity-50"
            >
              {saving ? "Saving…" : "Add loan"}
            </button>
          </div>
        </>
      )}
    </Card>
  );
}

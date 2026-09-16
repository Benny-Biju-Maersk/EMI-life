"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

// The auth check (redirect to /sign-in if not signed in) lives in
// app/onboarding/page.tsx, a Server Component — this stays a plain Client
// Component so it can use hooks (useState, useRouter). Same split as
// app/dashboard/page.tsx vs its widgets, just one level up since this
// page has no separate small widgets to split further.

type Loan = {
  name: string;
  principal: number;
  annual_rate_pct: number;
  tenure_months: number;
  months_paid: number;
};

const STEPS = ["Income & savings", "Your loans", "Monthly expenses"] as const;

export function OnboardingForm() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);

  // Step 1
  const [income, setIncome] = useState("");
  const [savings, setSavings] = useState("");

  // Step 2
  const [loans, setLoans] = useState<Loan[]>([]);
  const [loanName, setLoanName] = useState("");
  const [loanPrincipal, setLoanPrincipal] = useState("");
  const [loanRate, setLoanRate] = useState("");
  const [loanTenure, setLoanTenure] = useState("");

  // Step 3
  const [expenses, setExpenses] = useState<Record<string, number>>({});
  const [expCategory, setExpCategory] = useState("");
  const [expAmount, setExpAmount] = useState("");

  function addLoan() {
    if (!loanName || !loanPrincipal || !loanTenure) return;
    setLoans([
      ...loans,
      {
        name: loanName,
        principal: Number(loanPrincipal),
        annual_rate_pct: Number(loanRate || 0),
        tenure_months: Number(loanTenure),
        months_paid: 0,
      },
    ]);
    setLoanName("");
    setLoanPrincipal("");
    setLoanRate("");
    setLoanTenure("");
  }

  function addExpense() {
    if (!expCategory || !expAmount) return;
    setExpenses({ ...expenses, [expCategory]: Number(expAmount) });
    setExpCategory("");
    setExpAmount("");
  }

  async function finish() {
    setSubmitting(true);
    try {
      if (income) {
        await fetch("/api/profile", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ field: "monthly_income", value: income }),
        });
      }
      if (savings) {
        await fetch("/api/profile", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ field: "total_savings", value: savings }),
        });
      }
      if (loans.length > 0) {
        await fetch("/api/profile/loans", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ loans }),
        });
      }
      if (Object.keys(expenses).length > 0) {
        await fetch("/api/profile/expenses", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ expenses }),
        });
      }
      router.push("/dashboard");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-lg px-6 py-12">
      <h1 className="text-2xl font-semibold">Let&apos;s set up your portal</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        A few questions once, so every widget on your dashboard already
        knows your situation — nothing here is shared beyond building your
        own picture. Skip anything you&apos;d rather not share yet.
      </p>

      <div className="mt-6">
        <div className="flex gap-1.5">
          {STEPS.map((label, i) => (
            <div
              key={label}
              className={`h-1.5 flex-1 rounded-full transition-colors ${
                i <= step ? "bg-primary" : "bg-border"
              }`}
            />
          ))}
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          Step {step + 1} of {STEPS.length}: {STEPS[step]}
        </p>
      </div>

      <div className="mt-8">
        {step === 0 && (
          <div className="space-y-4 text-sm">
            <label className="block">
              <span className="text-muted-foreground">Monthly take-home income (₹)</span>
              <input
                type="number"
                value={income}
                onChange={(e) => setIncome(e.target.value)}
                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
            </label>
            <label className="block">
              <span className="text-muted-foreground">Total savings right now (₹)</span>
              <input
                type="number"
                value={savings}
                onChange={(e) => setSavings(e.target.value)}
                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
            </label>
          </div>
        )}

        {step === 1 && (
          <div className="text-sm">
            {loans.length > 0 && (
              <ul className="mb-4 space-y-1">
                {loans.map((l, i) => (
                  <li key={i} className="flex justify-between text-foreground">
                    <span>{l.name}</span>
                    <span>
                      ₹{l.principal.toLocaleString("en-IN")} · {l.annual_rate_pct}% ·{" "}
                      {l.tenure_months}mo
                    </span>
                  </li>
                ))}
              </ul>
            )}
            <div className="grid grid-cols-2 gap-2">
              <input
                placeholder="Loan name (e.g. Car loan)"
                value={loanName}
                onChange={(e) => setLoanName(e.target.value)}
                className="col-span-2 rounded-md border border-border bg-background px-3 py-2 outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
              <input
                type="number"
                placeholder="Principal (₹)"
                value={loanPrincipal}
                onChange={(e) => setLoanPrincipal(e.target.value)}
                className="rounded-md border border-border bg-background px-3 py-2 outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
              <input
                type="number"
                placeholder="Rate (%/yr)"
                value={loanRate}
                onChange={(e) => setLoanRate(e.target.value)}
                className="rounded-md border border-border bg-background px-3 py-2 outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
              <input
                type="number"
                placeholder="Tenure (months)"
                value={loanTenure}
                onChange={(e) => setLoanTenure(e.target.value)}
                className="col-span-2 rounded-md border border-border bg-background px-3 py-2 outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
            </div>
            <button
              type="button"
              onClick={addLoan}
              className="mt-2 rounded-md border border-border px-4 py-1.5 text-sm hover:bg-border/40"
            >
              + Add loan
            </button>
            <p className="mt-2 text-xs text-muted-foreground/70">No loans? Just move on.</p>
          </div>
        )}

        {step === 2 && (
          <div className="text-sm">
            {Object.keys(expenses).length > 0 && (
              <ul className="mb-4 space-y-1">
                {Object.entries(expenses).map(([k, v]) => (
                  <li key={k} className="flex justify-between text-foreground">
                    <span className="capitalize">{k}</span>
                    <span>₹{v.toLocaleString("en-IN")}</span>
                  </li>
                ))}
              </ul>
            )}
            <div className="flex gap-2">
              <input
                placeholder="Category (e.g. rent)"
                value={expCategory}
                onChange={(e) => setExpCategory(e.target.value)}
                className="flex-1 rounded-md border border-border bg-background px-3 py-2 outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
              <input
                type="number"
                placeholder="₹/month"
                value={expAmount}
                onChange={(e) => setExpAmount(e.target.value)}
                className="w-32 rounded-md border border-border bg-background px-3 py-2 outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
            </div>
            <button
              type="button"
              onClick={addExpense}
              className="mt-2 rounded-md border border-border px-4 py-1.5 text-sm hover:bg-border/40"
            >
              + Add category
            </button>
          </div>
        )}
      </div>

      <div className="mt-8 flex justify-between">
        <button
          type="button"
          onClick={() => setStep((s) => Math.max(0, s - 1))}
          disabled={step === 0}
          className="rounded-md px-4 py-1.5 text-sm text-muted-foreground disabled:opacity-0"
        >
          ← Back
        </button>
        {step < STEPS.length - 1 ? (
          <button
            type="button"
            onClick={() => setStep((s) => s + 1)}
            className="rounded-md bg-primary px-6 py-1.5 text-sm text-primary-foreground hover:bg-primary/90"
          >
            Next →
          </button>
        ) : (
          <button
            type="button"
            onClick={finish}
            disabled={submitting}
            className="rounded-md bg-primary px-6 py-1.5 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {submitting ? "Setting up…" : "Go to my dashboard"}
          </button>
        )}
      </div>
    </div>
  );
}

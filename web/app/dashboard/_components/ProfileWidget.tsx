"use client";

import { useEffect, useState } from "react";
import { Card, NumberField } from "./shared";

// Calls THIS app's own /api/profile route (app/api/profile/route.ts),
// never api/main.py directly — that route is what verifies who's actually
// signed in before touching tools/user_profile.py's tier-3 store. See its
// comment and api/main.py's module docstring for the full trust-boundary
// reasoning.
//
// Loans and itemized expenses moved to their own widgets
// (LoansWidget/ExpensesWidget, tools/financial_profile.py) once those
// needed real structure — this widget now just owns the two true scalars.

type Profile = Record<string, string>;

export function ProfileWidget() {
  const [profile, setProfile] = useState<Profile>({});
  const [income, setIncome] = useState("");
  const [savings, setSavings] = useState("");
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    fetch("/api/profile")
      .then((r) => r.json())
      .then((data) => {
        const p: Profile = data.profile ?? {};
        setProfile(p);
        setIncome(p.monthly_income ?? "");
        setSavings(p.total_savings ?? "");
      })
      .finally(() => setLoaded(true));
  }, []);

  async function save() {
    setSaving(true);
    try {
      const fields: [string, string][] = [
        ["monthly_income", income],
        ["total_savings", savings],
      ];
      for (const [field, value] of fields) {
        if (value === "") continue;
        await fetch("/api/profile", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ field, value }),
        });
      }
      const res = await fetch("/api/profile");
      const data = await res.json();
      setProfile(data.profile ?? {});
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card title="My Profile">
      <p className="text-xs text-muted-foreground">
        Saved once, reused everywhere — Budget Snapshot, My Loans, and
        What&apos;s Happening For You all read this without asking you to
        repeat yourself.
      </p>
      {!loaded ? (
        <p className="mt-3 text-sm text-muted-foreground">Loading…</p>
      ) : (
        <>
          <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
            <NumberField label="Monthly income (₹)" value={income} onChange={setIncome} />
            <NumberField label="Total savings (₹)" value={savings} onChange={setSavings} />
          </div>
          <button
            type="button"
            onClick={save}
            disabled={saving}
            className="mt-3 w-full rounded-md bg-primary py-1.5 text-sm text-primary-foreground transition hover:bg-primary/90 disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save"}
          </button>
          {Object.keys(profile).length === 0 && (
            <p className="mt-2 text-xs text-muted-foreground/70">Nothing saved yet.</p>
          )}
        </>
      )}
    </Card>
  );
}

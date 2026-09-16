"use client";

import { useEffect, useState } from "react";
import { Card, Row } from "./shared";

type Snapshot = {
  foir_pct?: number;
  total_monthly_emis?: number;
  verdict?: string;
  monthly_surplus_after_emis?: number;
};

type SnapshotResponse = {
  snapshot: Snapshot | null;
  note?: string;
  error?: string;
};

export function BudgetSnapshotWidget() {
  const [data, setData] = useState<SnapshotResponse | null>(null);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    fetch("/api/budget-snapshot")
      .then((r) => r.json())
      .then(setData)
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  return (
    <Card title="Budget Snapshot">
      <p className="text-xs text-muted-foreground">
        Reads My Profile, below — no new purchase, just where things stand
        today.
      </p>
      {loading ? (
        <p className="mt-3 text-sm text-muted-foreground">Loading…</p>
      ) : data?.error ? (
        <p className="mt-3 text-sm text-destructive">{data.error}</p>
      ) : !data?.snapshot ? (
        <p className="mt-3 text-sm text-muted-foreground">
          {data?.note ?? "Save your income in My Profile to see this."}
        </p>
      ) : (
        <>
          <p className="mt-3 text-lg font-semibold capitalize">
            {data.snapshot.verdict?.replace(/_/g, " ")}
          </p>
          <dl className="mt-2 space-y-1 text-sm">
            <Row label="Current monthly EMIs" value={data.snapshot.total_monthly_emis} />
            <Row label="FOIR" value={`${data.snapshot.foir_pct}%`} />
            {data.snapshot.monthly_surplus_after_emis !== undefined && (
              <Row label="Surplus after essentials" value={data.snapshot.monthly_surplus_after_emis} />
            )}
          </dl>
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

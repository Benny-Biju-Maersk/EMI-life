"use client";

import { useState } from "react";
import { API_URL, Card, NumberField, Row } from "./shared";

type EmiResult = {
  emi?: number;
  total_interest?: number;
  total_payment?: number;
  error?: string;
};

export function EmiCalculatorWidget() {
  const [principal, setPrincipal] = useState("500000");
  const [rate, setRate] = useState("10");
  const [tenure, setTenure] = useState("24");
  const [result, setResult] = useState<EmiResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function calculate() {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/calculate-emi`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          principal: Number(principal),
          annual_rate_pct: Number(rate),
          tenure_months: Number(tenure),
        }),
      });
      setResult(await res.json());
    } catch {
      setResult({ error: "Couldn't reach the API" });
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card title="EMI Calculator">
      <div className="grid grid-cols-3 gap-2 text-sm">
        <NumberField label="Principal (₹)" value={principal} onChange={setPrincipal} />
        <NumberField label="Rate (%/yr)" value={rate} onChange={setRate} />
        <NumberField label="Tenure (months)" value={tenure} onChange={setTenure} />
      </div>
      <button
        type="button"
        onClick={calculate}
        disabled={loading}
        className="mt-3 w-full rounded-md bg-primary py-1.5 text-sm text-primary-foreground transition hover:bg-primary/90 disabled:opacity-50"
      >
        {loading ? "Calculating…" : "Calculate"}
      </button>
      {result &&
        (result.error ? (
          <p className="mt-3 text-sm text-destructive">{result.error}</p>
        ) : (
          <dl className="mt-3 space-y-1 text-sm">
            <Row label="Monthly EMI" value={result.emi} />
            <Row label="Total interest" value={result.total_interest} />
            <Row label="Total payment" value={result.total_payment} />
          </dl>
        ))}
    </Card>
  );
}

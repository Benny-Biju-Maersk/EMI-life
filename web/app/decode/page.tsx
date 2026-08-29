"use client";

import { useState, type FormEvent } from "react";

// tools/finance_tools.py:decode_emi_offer's return shape (see
// docs/decision.md #11) — this page never computes anything itself, it
// only renders what api/main.py's /decode-offer endpoint returns, same
// "logic lives once" convention as every other surface in this repo.
type DecodeResult = {
  monthly_emi?: number;
  sticker_total?: number;
  processing_fee_with_gst?: number;
  forfeited_discount?: number;
  hidden_cost?: number;
  effective_total_cost?: number;
  verdict?: string;
  error?: string;
  affordability?: {
    verdict: string;
    foir_pct: number;
    total_monthly_emis: number;
  };
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export default function DecodePage() {
  const [itemPrice, setItemPrice] = useState("");
  const [tenureMonths, setTenureMonths] = useState("12");
  const [processingFee, setProcessingFee] = useState("0");
  const [forfeitedDiscount, setForfeitedDiscount] = useState("0");
  const [monthlyIncome, setMonthlyIncome] = useState("");
  const [existingEmis, setExistingEmis] = useState("0");
  const [result, setResult] = useState<DecodeResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch(`${API_URL}/decode-offer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          item_price: Number(itemPrice),
          tenure_months: Number(tenureMonths),
          processing_fee: Number(processingFee),
          forfeited_discount: Number(forfeitedDiscount),
          monthly_net_income: monthlyIncome ? Number(monthlyIncome) : null,
          existing_emis: Number(existingEmis),
        }),
      });
      const data: DecodeResult = await res.json();
      setResult(data);
    } catch {
      setResult({
        error:
          "Couldn't reach FinBuddy's API — is it running? (uvicorn api.main:app --reload --port 8001)",
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl px-6 py-12">
      <h1 className="text-2xl font-semibold">Decode this EMI offer</h1>
      <p className="mt-2 text-sm text-gray-600">
        Fill in what the checkout screen shows you. Leave income blank if
        you&apos;d rather not share it yet — you&apos;ll still get the true
        cost, just not an affordability verdict.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <Field
          label="Item price (₹)"
          value={itemPrice}
          onChange={setItemPrice}
          required
        />
        <Field
          label="Tenure (months)"
          value={tenureMonths}
          onChange={setTenureMonths}
          required
        />
        <Field
          label="Processing fee (₹, before GST)"
          value={processingFee}
          onChange={setProcessingFee}
        />
        <Field
          label="Forfeited discount / cashback (₹)"
          value={forfeitedDiscount}
          onChange={setForfeitedDiscount}
        />
        <hr className="my-4 border-gray-200" />
        <Field
          label="Your monthly income (₹, optional)"
          value={monthlyIncome}
          onChange={setMonthlyIncome}
        />
        <Field
          label="Existing monthly EMIs (₹)"
          value={existingEmis}
          onChange={setExistingEmis}
        />

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-md bg-black py-2 text-white transition hover:bg-gray-800 disabled:opacity-50"
        >
          {loading ? "Decoding…" : "Decode it"}
        </button>
      </form>

      {result && (
        <div className="mt-8 rounded-md border border-gray-200 p-4">
          {result.error ? (
            <p className="text-red-600">{result.error}</p>
          ) : (
            <>
              <p className="text-lg font-semibold">
                {result.verdict === "actually no-cost"
                  ? "✅ Actually no-cost"
                  : "⚠️ Has a hidden cost"}
              </p>
              <dl className="mt-3 space-y-1 text-sm">
                <Row label="Monthly EMI" value={result.monthly_emi} />
                <Row label="Hidden cost" value={result.hidden_cost} />
                <Row
                  label="Effective total cost"
                  value={result.effective_total_cost}
                />
              </dl>
              {result.affordability && (
                <div className="mt-4 border-t border-gray-200 pt-3 text-sm">
                  <p className="font-medium">
                    Affordability:{" "}
                    {result.affordability.verdict.replace(/_/g, " ")}
                  </p>
                  <p className="text-gray-600">
                    FOIR after this EMI: {result.affordability.foir_pct}%
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  required,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  required?: boolean;
}) {
  return (
    <label className="block text-sm">
      <span className="text-gray-700">{label}</span>
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 focus:border-black focus:outline-none"
      />
    </label>
  );
}

function Row({ label, value }: { label: string; value?: number }) {
  if (value === undefined) return null;
  return (
    <div className="flex justify-between">
      <dt className="text-gray-600">{label}</dt>
      <dd>₹{value.toLocaleString("en-IN")}</dd>
    </div>
  );
}

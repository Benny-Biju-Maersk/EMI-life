import { auth } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

// Same trust-boundary pattern as app/api/profile/route.ts.
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export async function POST(request: Request) {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }
  const body = await request.json();

  // Auto-fill context from the user's saved profile (same numbers
  // BudgetSnapshotWidget already shows) so every panelist reasons from
  // real income/EMIs instead of the user retyping what they've already
  // told FinBuddy once — reuses api/main.py's own aggregation rather than
  // re-deriving it here. A caller-supplied body.context still wins if
  // given (e.g. the widget lets someone override it for a hypothetical).
  let autoContext: Record<string, unknown> | undefined;
  try {
    const snapshotRes = await fetch(
      `${API_URL}/budget-snapshot?user_id=${encodeURIComponent(userId)}`,
    );
    const snapshot = await snapshotRes.json();
    const income = snapshot?.profile?.monthly_income;
    if (income) {
      autoContext = {
        monthly_net_income: Number(income),
        existing_emis: snapshot?.snapshot?.total_monthly_emis ?? 0,
      };
    }
  } catch {
    // A missing/unreachable profile shouldn't block asking the council —
    // it just reasons without personalized numbers, same as the original
    // standalone /decode page's "leave income blank" path.
  }

  const res = await fetch(`${API_URL}/council`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...body,
      user_id: userId,
      context: body.context ?? autoContext,
    }),
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

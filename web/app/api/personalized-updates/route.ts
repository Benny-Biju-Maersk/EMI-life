import { auth } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

// Same trust-boundary pattern as app/api/profile/route.ts. This one also
// triggers a real LLM call server-side (tools/personalized_insights.py)
// — still fine to proxy the same way, the cost/latency is on api/main.py,
// not this route.
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export async function GET() {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }
  const res = await fetch(`${API_URL}/personalized-updates?user_id=${encodeURIComponent(userId)}`);
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

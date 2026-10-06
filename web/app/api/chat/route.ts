import { auth } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

// Same trust-boundary pattern as app/api/profile/route.ts — see that
// file's comment and api/main.py's module docstring. The one difference
// from every other route here: api/main.py's /chat hits the full
// multi-agent supervisor graph (agents/web_graph.py), not a single
// tools/*.py function, so this call can take noticeably longer (a
// specialist's tool calls, or the council's several parallel model calls).
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export async function POST(request: Request) {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }
  const body = await request.json();
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...body, user_id: userId }),
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

import { auth } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

// Same trust-boundary pattern as app/api/profile/route.ts.
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export async function GET() {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }
  const res = await fetch(`${API_URL}/profile/loans?user_id=${encodeURIComponent(userId)}`);
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

export async function POST(request: Request) {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }
  const body = await request.json();
  const res = await fetch(`${API_URL}/profile/loans`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...body, user_id: userId }),
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

import { auth } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

// Same trust-boundary pattern as app/api/profile/route.ts.
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export async function GET() {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }
  const res = await fetch(`${API_URL}/budget-snapshot?user_id=${encodeURIComponent(userId)}`);
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

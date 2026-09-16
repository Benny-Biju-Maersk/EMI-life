import { auth } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

// Server-side only (route handlers run on the server, never in the
// browser) — this is what makes the trust boundary in api/main.py's
// module docstring hold: auth() is verified here, then userId is passed
// to the Python API ourselves. The browser calls THIS route, never
// api/main.py's /profile directly, and never gets to say whose data it
// wants.
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export async function GET() {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }
  const res = await fetch(`${API_URL}/profile?user_id=${encodeURIComponent(userId)}`);
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

export async function POST(request: Request) {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }
  const body = await request.json();
  const res = await fetch(`${API_URL}/profile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...body, user_id: userId }),
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

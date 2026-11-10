import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  try {
    const body = await req.json().catch(() => ({}));
    const username = (body.username || "").trim();
    const password = (body.password || "").trim();

    if (!username || !password) {
      return NextResponse.json(
        { detail: "Missing administrative username or password" },
        { status: 400 }
      );
    }

    // 1. Try the admin API on port 8000
    const adminApi = process.env.NEXT_PUBLIC_ADMIN_API_URL || "http://localhost:8000";
    try {
      const res = await fetch(`${adminApi}/api/v1/admin/auth/token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
        signal: AbortSignal.timeout(5000),
      });
      if (res.ok) {
        return NextResponse.json(await res.json());
      }
      if (res.status === 401) {
        const err = await res.json().catch(() => ({ detail: "Invalid credentials" }));
        return NextResponse.json(err, { status: 401 });
      }
    } catch {}

    // 2. Try the main backend on port 8000
    const backendApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    try {
      const res = await fetch(`${backendApi}/api/v1/admin/auth/token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
        signal: AbortSignal.timeout(5000),
      });
      if (res.ok) {
        return NextResponse.json(await res.json());
      }
      if (res.status === 401) {
        const err = await res.json().catch(() => ({ detail: "Invalid credentials" }));
        return NextResponse.json(err, { status: 401 });
      }
    } catch {}

    return NextResponse.json(
      { detail: "Authentication backend unavailable. Ensure the backend server is running." },
      { status: 503 }
    );
  } catch (err: any) {
    return NextResponse.json(
      { detail: err.message || "Internal auth error" },
      { status: 500 }
    );
  }
}

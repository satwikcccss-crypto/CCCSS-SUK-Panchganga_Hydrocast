import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

type Bucket = { count: number; resetAt: number };
const RATE_WINDOW_MS = 60_000;
const RATE_MAX = 10;
const buckets = new Map<string, Bucket>();

function getClientIp(req: Request): string {
  const xf = req.headers.get("x-forwarded-for");
  if (xf) return xf.split(",")[0].trim() || "unknown";
  return req.headers.get("x-real-ip") || "unknown";
}

function rateLimited(ip: string): boolean {
  const now = Date.now();
  const b = buckets.get(ip);
  if (!b || now >= b.resetAt) {
    buckets.set(ip, { count: 1, resetAt: now + RATE_WINDOW_MS });
    if (buckets.size > 5000) {
      for (const [k, v] of buckets) if (now >= v.resetAt) buckets.delete(k);
    }
    return false;
  }
  b.count += 1;
  return b.count > RATE_MAX;
}

function backendOrigin(): string {
  const origin =
    process.env.ADMIN_BACKEND_ORIGIN ||
    process.env.ADMIN_API_ORIGIN ||
    "http://127.0.0.1:8001";
  return origin.replace(/\/+$/, "");
}

export async function POST(req: Request) {
  const ip = getClientIp(req);
  if (rateLimited(ip)) {
    return NextResponse.json(
      { detail: "Too many authentication attempts. Please try again later." },
      { status: 429, headers: { "Retry-After": "60" } }
    );
  }

  try {
    const body = await req.json().catch(() => null);
    const username = typeof body?.username === "string" ? body.username.trim() : "";
    const password = typeof body?.password === "string" ? body.password : "";

    if (!username || !password) {
      return NextResponse.json(
        { detail: "Missing administrative username or password" },
        { status: 400 }
      );
    }
    if (username.length > 128 || password.length > 256) {
      return NextResponse.json({ detail: "Invalid credentials payload" }, { status: 400 });
    }

    const target = backendOrigin();
    let res: Response;
    try {
      res = await fetch(`${target}/api/v1/admin/auth/token`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ username, password }),
        cache: "no-store",
        signal: AbortSignal.timeout(8000),
      });
    } catch {
      return NextResponse.json(
        { detail: "Authentication service unavailable" },
        { status: 503 }
      );
    }

    const contentType = res.headers.get("content-type") || "";
    const payload = contentType.includes("application/json")
      ? await res.json().catch(() => null)
      : null;

    if (res.ok) {
      return NextResponse.json(payload ?? {});
    }

    if (res.status === 400 || res.status === 401 || res.status === 403 || res.status === 429) {
      const detail =
        payload && typeof payload.detail === "string"
          ? payload.detail
          : res.status === 429
            ? "Too many authentication attempts. Please try again later."
            : res.status === 401 || res.status === 403
              ? "Invalid credentials"
              : "Invalid request";
      return NextResponse.json({ detail }, { status: res.status });
    }

    return NextResponse.json(
      { detail: "Authentication service unavailable" },
      { status: 503 }
    );
  } catch {
    return NextResponse.json({ detail: "Authentication request failed" }, { status: 500 });
  }
}

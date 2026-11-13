import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || process.env.BACKEND_ORIGIN || "http://localhost:8000";
const ADMIN_API = process.env.NEXT_PUBLIC_ADMIN_API_URL || process.env.ADMIN_BACKEND_ORIGIN || "http://localhost:8001";

function bearer(req: Request): string | null {
  const h = req.headers.get("authorization") || "";
  return h.toLowerCase().startsWith("bearer ") ? h.slice(7).trim() || null : null;
}

export async function GET(req: Request) {
  const token = bearer(req);
  if (!token) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  // Try admin API first, then public backend endpoint with forwarded bearer token.
  for (const base of [ADMIN_API, BACKEND_URL]) {
    try {
      const res = await fetch(`${base}/api/v1/db-health`, {
        headers: { "Cache-Control": "no-store", Authorization: `Bearer ${token}` },
        cache: "no-store",
        signal: AbortSignal.timeout(4000),
      });
      if (res.ok) return NextResponse.json(await res.json());
    } catch {
      /* try next */
    }
  }

  return NextResponse.json({ ok: false, error: "Database health unavailable" }, { status: 503 });
}


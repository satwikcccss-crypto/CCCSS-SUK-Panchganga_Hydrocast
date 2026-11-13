import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const ADMIN_API = process.env.NEXT_PUBLIC_ADMIN_API_URL || process.env.ADMIN_BACKEND_ORIGIN || "http://localhost:8001";

function bearer(req: Request): string | null {
  const h = req.headers.get("authorization") || "";
  return h.toLowerCase().startsWith("bearer ") ? h.slice(7).trim() || null : null;
}

export async function GET(req: Request) {
  const token = bearer(req);
  if (!token) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  try {
    const res = await fetch(`${ADMIN_API}/api/v1/admin/health-log`, {
      headers: { "Cache-Control": "no-store", Authorization: `Bearer ${token}` },
      cache: "no-store",
      signal: AbortSignal.timeout(4000),
    });
    return NextResponse.json(await res.json().catch(() => ({})), { status: res.status });
  } catch {
    return NextResponse.json({ error: "Admin backend unavailable" }, { status: 503 });
  }
}

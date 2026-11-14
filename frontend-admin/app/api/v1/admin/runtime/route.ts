import { NextResponse } from "next/server";
import { isAdminUnlocked, getAdminClaims, bearer } from "@/lib/server/admin_auth";

export const dynamic = "force-dynamic";

const ADMIN_API = process.env.NEXT_PUBLIC_ADMIN_API_URL || process.env.ADMIN_BACKEND_ORIGIN || "http://localhost:8001";

export async function GET(req: Request) {
  const token = bearer(req);
  if (!token) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const verdict = await getAdminClaims(req);
  if (verdict.status !== "authorized") {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  if (!isAdminUnlocked(verdict.claims)) {
    return NextResponse.json({ error: "Official/viewer accounts have read-only access" }, { status: 403 });
  }

  try {
    const res = await fetch(`${ADMIN_API}/api/v1/admin/runtime`, {
      headers: { "Cache-Control": "no-store", Authorization: `Bearer ${token}` },
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    return NextResponse.json(await res.json().catch(() => ({})), { status: res.status });
  } catch {
    return NextResponse.json({ error: "Admin backend unavailable" }, { status: 503 });
  }
}

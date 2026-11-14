import { NextResponse } from "next/server";
import { bearer, getAdminClaims } from "@/lib/server/admin_auth";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const token = bearer(req);
  if (!token) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const verdict = await getAdminClaims(req);
  if (verdict.status === "unauthorized") {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  if (verdict.status === "unavailable") {
    return NextResponse.json({ error: "Admin service unavailable" }, { status: 503 });
  }

  const publicUrl = process.env.PUBLIC_PORTAL_URL || "http://127.0.0.1:3000";
  const start = performance.now();
  try {
    const res = await fetch(publicUrl, {
      method: "GET",
      cache: "no-store",
      signal: AbortSignal.timeout(3000),
    });
    const latency_ms = Math.round(performance.now() - start);
    return NextResponse.json({
      ok: res.ok,
      status: res.status,
      latency_ms,
      url: publicUrl,
    });
  } catch (err: any) {
    return NextResponse.json({
      ok: false,
      status: 503,
      error: err?.message || "Public portal unreachable",
      url: publicUrl,
    });
  }
}


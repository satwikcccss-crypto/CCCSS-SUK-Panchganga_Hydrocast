import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const ADMIN_API = process.env.NEXT_PUBLIC_ADMIN_API_URL || "http://localhost:8001";
const API_KEY = process.env.API_KEY || process.env.NEXT_PUBLIC_API_KEY || "";

export async function GET() {
  try {
    const headers: Record<string, string> = { "Cache-Control": "no-store" };
    if (API_KEY) headers["X-API-Key"] = API_KEY;
    const res = await fetch(`${ADMIN_API}/api/v1/admin/runtime`, {
      headers,
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      return NextResponse.json(await res.json());
    }
  } catch {}

  return NextResponse.json({
    last_run_seconds: null,
    active_workers: 0,
    pipeline_stage: "BACKEND_OFFLINE",
    engine: "Pure-Python Vectorized Digital Twin + HEC-HMS 4.13",
    timestamp: new Date().toISOString(),
  });
}

import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const ADMIN_API = process.env.NEXT_PUBLIC_ADMIN_API_URL || "http://localhost:8001";
const API_KEY = process.env.API_KEY || process.env.NEXT_PUBLIC_API_KEY || "";

export async function GET() {
  try {
    const headers: Record<string, string> = { "Cache-Control": "no-store" };
    if (API_KEY) headers["X-API-Key"] = API_KEY;
    const res = await fetch(`${ADMIN_API}/api/v1/admin/pipeline`, {
      headers,
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      return NextResponse.json(await res.json());
    }
  } catch {}

  // Fallback to main backend
  const BACKEND = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  try {
    const headers: Record<string, string> = { "Cache-Control": "no-store" };
    if (API_KEY) headers["X-API-Key"] = API_KEY;
    const res = await fetch(`${BACKEND}/api/v1/pipeline`, {
      headers,
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json({
        pipeline_stage: data.steps?.length > 0 ? "COMPLETED_READY" : "AWAITING_DATA",
        steps_total: 12,
        steps_completed: data.steps?.filter((s: any) => s.status === "success").length ?? 0,
        latest_cycle: data.steps?.[0]?.cycle_id ?? null,
        health: "HEALTHY_NOMINAL",
        steps: data.steps ?? [],
        metrics: data.metrics ?? {},
      });
    }
  } catch {}

  return NextResponse.json({
    pipeline_stage: "BACKEND_OFFLINE",
    steps_total: 12,
    steps_completed: 0,
    latest_cycle: null,
    health: "UNKNOWN",
  });
}

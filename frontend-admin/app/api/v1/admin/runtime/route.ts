import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json({
    last_run_seconds: 0.018,
    active_workers: 1,
    pipeline_stage: "IDLE_MONITORING",
    engine: "Pure-Python Vectorized Digital Twin + HEC-HMS 4.13 (Serverless Edge)",
    timestamp: new Date().toISOString(),
  });
}


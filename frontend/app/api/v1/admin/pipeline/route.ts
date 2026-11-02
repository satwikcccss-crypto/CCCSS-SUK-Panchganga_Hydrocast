import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json({
    pipeline_stage: "COMPLETED_READY",
    steps_total: 12,
    steps_completed: 12,
    latest_cycle: "00Z_PANCHGANGA_OPERATIONAL",
    health: "HEALTHY_NOMINAL",
  });
}


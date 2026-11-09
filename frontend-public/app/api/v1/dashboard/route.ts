import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const run_id = searchParams.get("run_id");

  // Proxy to the backend FastAPI /api/v1/dashboard — single source of truth
  // so Public and Admin dashboards always show identical forecast data.
  try {
    const targetUrl = new URL(`${BACKEND_URL}/api/v1/dashboard`);
    if (run_id) targetUrl.searchParams.set("run_id", run_id);
    const res = await fetch(targetUrl.toString(), {
      headers: { "Cache-Control": "no-store, no-cache, must-revalidate" },
      cache: "no-store",
    });
    if (!res.ok) {
      return NextResponse.json({ error: `Backend returned ${res.status}` }, { status: res.status });
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    // Fallback: backend unreachable — return clean empty state
    return NextResponse.json({
      ecmwf: {},
      stations: [],
      gauges: {},
      hydrograph: [],
      bridgeShivaji: { site: null, forecast: [] },
      bridgeRajaram: { site: null, forecast: [] },
      subbasins: [],
      runs_history: [],
      pipeline: {
        stage: "AWAITING_DATA",
        cycle: null,
        next_run_in_mins: null,
        components: {
          open_meteo: "OFFLINE",
          stage_rating: "OFFLINE",
          database: "OFFLINE",
          hec_hms: "OFFLINE",
        },
        steps: [],
        metrics: { avg_duration_s: 0, success_rate_pct: 0 },
      },
      status: {
        system: "backend_unreachable",
        last_cycle: null,
      },
      logs: [],
    });
  }
}

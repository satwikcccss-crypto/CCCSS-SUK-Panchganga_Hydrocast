import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET() {
  // Read the real pipeline state dumped by the Python hydrology runner
  const candidates = [
    path.join(process.cwd(), "public", "data", "latest_pipeline_state.json"),
    path.join(process.cwd(), "..", "data", "openmeteo_dss", "latest_pipeline_state.json"),
    path.join(process.cwd(), "data", "openmeteo_dss", "latest_pipeline_state.json"),
  ];

  for (const pipelineFile of candidates) {
    try {
      if (fs.existsSync(pipelineFile)) {
        const raw = fs.readFileSync(pipelineFile, "utf-8");
        const data = JSON.parse(raw);
        return NextResponse.json(data);
      }
    } catch (err) {
      console.error("Failed to read pipeline state file:", err);
    }
  }

  // No pipeline data available — return a clean empty state
  // The frontend components will show "Awaiting data" indicators
  return NextResponse.json({
    ecmwf: {},
    stations: [],
    gauges: {},
    hydrograph: [],
    bridgeShivaji: { site: null, forecast: [] },
    bridgeRajaram: { site: null, forecast: [] },
    subbasins: [],
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
      system: "awaiting_first_run",
      last_cycle: null,
    },
    logs: [],
  });
}

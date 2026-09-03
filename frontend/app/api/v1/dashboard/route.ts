import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const requestedRunId = searchParams.get("run_id");

  // If a specific historical run is requested, attempt to serve it directly
  if (requestedRunId) {
    const runCandidates = [
      path.join(process.cwd(), "..", "data", "runs", `${requestedRunId}.json`),
      path.join(process.cwd(), "public", "data", "runs", `${requestedRunId}.json`),
      path.join(process.cwd(), "data", "runs", `${requestedRunId}.json`),
    ];

    for (const file of runCandidates) {
      if (fs.existsSync(file)) {
        try {
          const raw = fs.readFileSync(file, "utf-8");
          const runData = JSON.parse(raw);
          // Attach runs_history ledger if available
          const historyFile = path.join(process.cwd(), "public", "data", "runs_history.json");
          if (fs.existsSync(historyFile)) {
            runData.runs_history = JSON.parse(fs.readFileSync(historyFile, "utf-8"));
          }
          return NextResponse.json(runData);
        } catch (err) {
          console.error(`Failed to read run file ${file}:`, err);
        }
      }
    }
  }

  // Read the latest pipeline state dumped by the Python hydrology runner
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

        // Ensure runs_history is attached
        if (!data.runs_history || data.runs_history.length === 0) {
          const historyCandidates = [
            path.join(process.cwd(), "public", "data", "runs_history.json"),
            path.join(process.cwd(), "..", "data", "runs", "runs_index.json"),
            path.join(process.cwd(), "data", "runs", "runs_index.json"),
          ];
          for (const hFile of historyCandidates) {
            if (fs.existsSync(hFile)) {
              try {
                data.runs_history = JSON.parse(fs.readFileSync(hFile, "utf-8"));
                break;
              } catch (e) {
                console.error("Failed to parse history file:", e);
              }
            }
          }
        }

        return NextResponse.json(data);
      }
    } catch (err) {
      console.error("Failed to read pipeline state file:", err);
    }
  }

  // No pipeline data available — return a clean empty state
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
      system: "awaiting_first_run",
      last_cycle: null,
    },
    logs: [],
  });
}

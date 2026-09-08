import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET(req: Request) {
  // 1. Verify the API Key
  const apiKeyHeader = req.headers.get("x-api-key");
  const validApiKey = process.env.API_KEY;

  if (!validApiKey) {
    return NextResponse.json(
      { error: "Server API Key not configured. Set API_KEY in environment variables." },
      { status: 500 }
    );
  }

  if (apiKeyHeader !== validApiKey) {
    return NextResponse.json(
      { error: "Unauthorized. Invalid or missing X-API-Key header." },
      { status: 401 }
    );
  }

  // 2. Fetch the latest pipeline state
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

  return NextResponse.json(
    { error: "Data not available. Forecast cycle has not run yet." },
    { status: 404 }
  );
}

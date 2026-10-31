import { NextResponse } from "next/server";
import crypto from "crypto";
import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";
export const revalidate = 0;

// Constant-time comparison so the API key cannot be recovered byte-by-byte
// through response-timing differences.
function safeEqual(a: string | null, b: string | null): boolean {
  if (!a || !b) return false;
  const ab = Buffer.from(a);
  const bb = Buffer.from(b);
  return ab.length === bb.length && crypto.timingSafeEqual(ab, bb);
}

export async function GET(req: Request) {
  // 1. Verify the API Key
  const apiKeyHeader = req.headers.get("x-api-key");
  const validApiKey = process.env.API_KEY;

  if (!validApiKey) {
    // Generic message: do not reveal server configuration state to callers.
    return NextResponse.json({ error: "Export endpoint unavailable" }, { status: 503 });
  }

  if (!safeEqual(apiKeyHeader, validApiKey)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
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

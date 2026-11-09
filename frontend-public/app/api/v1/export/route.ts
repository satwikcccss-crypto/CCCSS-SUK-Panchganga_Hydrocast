import { NextResponse } from "next/server";
import crypto from "crypto";
import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";
export const revalidate = 0;

function safeEqual(a: string | null, b: string | null): boolean {
  if (!a || !b) return false;
  const ab = Buffer.from(a);
  const bb = Buffer.from(b);
  return ab.length === bb.length && crypto.timingSafeEqual(ab, bb);
}

export async function GET(req: Request) {
  const apiKeyHeader = req.headers.get("x-api-key");
  const validApiKey = process.env.API_KEY;

  if (!validApiKey) {
    return NextResponse.json({ error: "Export endpoint unavailable" }, { status: 503 });
  }

  if (!safeEqual(apiKeyHeader, validApiKey)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const cwd = process.cwd();
  const root = (cwd.endsWith("frontend-public") || cwd.endsWith("frontend-admin") || cwd.endsWith("frontend"))
    ? path.resolve(cwd, "..")
    : cwd;

  const pipelineFile = path.join(root, "data", "openmeteo_dss", "latest_pipeline_state.json");

  if (fs.existsSync(pipelineFile)) {
    try {
      const raw = fs.readFileSync(pipelineFile, "utf-8");
      return NextResponse.json(JSON.parse(raw));
    } catch (err) {
      console.error("Failed to read pipeline state file:", err);
    }
  }

  return NextResponse.json(
    { error: "Data not available. Forecast cycle has not run yet." },
    { status: 404 }
  );
}

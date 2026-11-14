import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { bearer, getAdminClaims } from "@/lib/server/admin_auth";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET(req: Request) {
  const token = bearer(req);
  if (!token) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const verdict = await getAdminClaims(req);
  if (verdict.status === "unauthorized") {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  if (verdict.status === "unavailable") {
    return NextResponse.json({ error: "Admin service unavailable" }, { status: 503 });
  }

  // Fetch the latest pipeline state from local workspace artifacts (admin-only).
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

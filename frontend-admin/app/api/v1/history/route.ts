import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { bearer, getAdminClaims } from "@/lib/server/admin_auth";

export const dynamic = "force-dynamic";
export const revalidate = 0;

function getProjectPaths() {
  const cwd = process.cwd();
  const root = (cwd.endsWith("frontend-public") || cwd.endsWith("frontend-admin") || cwd.endsWith("frontend"))
    ? path.resolve(cwd, "..")
    : cwd;

  return {
    runsIndexFile: path.join(root, "data", "runs", "runs_index.json"),
  };
}

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

  const { runsIndexFile } = getProjectPaths();

  if (fs.existsSync(runsIndexFile)) {
    try {
      const raw = fs.readFileSync(runsIndexFile, "utf-8");
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) {
        return NextResponse.json(parsed);
      }
    } catch (err) {
      console.error("Failed to read runs_index.json:", err);
    }
  }

  return NextResponse.json([]);
}

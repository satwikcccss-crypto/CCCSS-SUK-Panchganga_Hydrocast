import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

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

export async function GET() {
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

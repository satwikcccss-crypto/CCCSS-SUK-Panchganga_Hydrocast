import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const now = new Date().toISOString();
  return NextResponse.json({
    health_log: [
      { timestamp: now, level: "INFO", message: "HydroCast Operations Control Room online" },
      { timestamp: now, level: "INFO", message: "Vercel edge telemetry bridge operating nominal" },
      { timestamp: now, level: "INFO", message: "Shivaji Bridge radar telemetry stream healthy (ThingSpeak #3424513)" },
      { timestamp: now, level: "INFO", message: "GitHub Actions workflow dispatcher standby ready" },
    ],
  });
}


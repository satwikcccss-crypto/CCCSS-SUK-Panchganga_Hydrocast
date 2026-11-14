import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

// Disabled on the operator console to avoid duplicate webhook surfaces and
// filesystem-coupled bot handling. Configure Telegram to use the public portal
// (or a single canonical backend endpoint) instead.
export async function POST() {
  return NextResponse.json(
    { ok: false, detail: "Telegram webhook is not enabled on the operator console." },
    { status: 410 }
  );
}

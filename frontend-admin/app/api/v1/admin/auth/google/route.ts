import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/**
 * Legacy endpoint disabled for Windows Server v1.1 hardening.
 * Client-side JWT minting with embedded secrets/allowlists is unsafe.
 * Use POST /api/v1/admin/auth/token (proxied to backend DB-backed auth).
 */
export async function POST() {
  return NextResponse.json(
    {
      detail:
        "Google sign-in is not available in this Windows Server deployment. Use administrator credentials via /api/v1/admin/auth/token.",
    },
    { status: 410 }
  );
}



import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/**
 * Disabled on Public Portal (Port 3000).
 * Administrative actions must be executed exclusively via Operator Console on Port 3001.
 */
export async function POST() {
  return NextResponse.json(
    {
      error: "Forbidden",
      detail:
        "Administrative pipeline triggers and DB dispatch actions are strictly disabled on the public portal. Access the HydroCast Operator Console on Port 3001.",
    },
    { status: 403 }
  );
}

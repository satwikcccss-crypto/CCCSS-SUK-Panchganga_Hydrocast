import { NextResponse } from "next/server";
import { bearer, getAdminClaims } from "@/lib/server/admin_auth";

export const dynamic = "force-dynamic";

function backendOrigin(): string {
  return (
    process.env.BACKEND_ORIGIN ||
    process.env.ADMIN_BACKEND_ORIGIN ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://127.0.0.1:8000"
  ).replace(/\/+$/, "");
}

export async function GET(req: Request) {
  const token = bearer(req);
  if (!token) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }
  const verdict = await getAdminClaims(req);
  if (verdict.status === "unauthorized") {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }
  if (verdict.status === "unavailable") {
    return NextResponse.json({ detail: "Admin service unavailable" }, { status: 503 });
  }

  try {
    const res = await fetch(`${backendOrigin()}/api/v1/sensors/live`, {
      cache: "no-store",
      headers: {
        "Cache-Control": "no-store",
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
      },
      signal: AbortSignal.timeout(8000),
    });

    const contentType = res.headers.get("content-type") || "";
    const payload = contentType.includes("application/json")
      ? await res.json().catch(() => null)
      : null;

    if (res.ok) {
      return NextResponse.json(payload ?? { stations: [], total: 0, online: 0 });
    }
    if (res.status === 401 || res.status === 403) {
      return NextResponse.json({ detail: "Unauthorized" }, { status: res.status });
    }
    return NextResponse.json({ detail: "Sensor backend unavailable" }, { status: 503 });
  } catch {
    return NextResponse.json({ detail: "Sensor backend unavailable" }, { status: 503 });
  }
}


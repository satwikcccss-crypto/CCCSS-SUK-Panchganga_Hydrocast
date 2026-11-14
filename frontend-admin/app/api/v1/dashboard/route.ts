import { NextResponse } from "next/server";
import { bearer, getAdminClaims } from "@/lib/server/admin_auth";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET(req: Request) {
  const token = bearer(req);
  if (!token) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  // Any valid console JWT (viewer or operator) may load the dashboard proxy.
  const verdict = await getAdminClaims(req);
  if (verdict.status === "unauthorized") {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  if (verdict.status === "unavailable") {
    return NextResponse.json({ error: "Admin service unavailable" }, { status: 503 });
  }

  const { searchParams } = new URL(req.url);
  const run_id = searchParams.get("run_id");

  // Proxy to the backend FastAPI /api/v1/dashboard — single source of truth
  // so Public and Admin dashboards always show identical forecast data.
  // Conditional-request semantics pass through so the proxy never defeats
  // the backend ETag/304 contract.
  const targetUrl = new URL(`${BACKEND_URL}/api/v1/dashboard`);
  if (run_id) targetUrl.searchParams.set("run_id", run_id);

  const incoming = req.headers.get("if-none-match");
  const upstreamHeaders: Record<string, string> = {
    "Cache-Control": "no-store, no-cache, must-revalidate",
    Authorization: `Bearer ${token}`,
  };
  if (incoming) upstreamHeaders["If-None-Match"] = incoming;

  let res: Response;
  try {
    res = await fetch(targetUrl.toString(), {
      headers: upstreamHeaders,
      cache: "no-store",
      signal: AbortSignal.timeout(6000),
    });
  } catch {
    return NextResponse.json({ error: "Backend unavailable" }, { status: 503 });
  }

  const etag = res.headers.get("etag");

  if (res.status === 304) {
    return new Response(null, {
      status: 304,
      headers: etag ? { ETag: etag, "Cache-Control": "no-cache" } : { "Cache-Control": "no-cache" },
    });
  }

  if (!res.ok) {
    const status = res.status >= 400 && res.status < 600 ? res.status : 503;
    return NextResponse.json({ error: `Backend returned ${res.status}` }, { status });
  }

  const data = await res.json().catch(() => null);
  if (data == null) {
    return NextResponse.json({ error: "Backend returned invalid payload" }, { status: 502 });
  }

  const body = NextResponse.json(data);
  if (etag) body.headers.set("ETag", etag);
  body.headers.set("Cache-Control", "no-cache");
  return body;
}

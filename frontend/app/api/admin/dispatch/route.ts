import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/**
 * POST /api/admin/dispatch
 * Local Windows Server Dispatch Route:
 * Proxies manual trigger commands from the Next.js console directly
 * to the local HydroCast FastAPI backend (:8000).
 */
export async function POST(req: Request) {
  try {
    const authHeader = req.headers.get("authorization");
    const cookieHeader = req.headers.get("cookie");

    let token: string | null = null;
    if (authHeader && authHeader.startsWith("Bearer ")) {
      token = authHeader.substring(7);
    } else if (cookieHeader) {
      const match = cookieHeader.match(/admin_token=([^;]+)/);
      if (match) token = match[1];
    }

    const { searchParams } = new URL(req.url);
    const targetPath = searchParams.get("path") || "/pipeline/trigger";

    const body = await req.json().catch(() => ({}));
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    const targetUrl = targetPath.startsWith("http")
      ? targetPath
      : `${apiBase}/api/v1/admin${targetPath.startsWith("/") ? targetPath : `/${targetPath}`}`;

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(targetUrl, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (err: any) {
    return NextResponse.json(
      { error: `Failed to dispatch command: ${err.message}` },
      { status: 500 }
    );
  }
}

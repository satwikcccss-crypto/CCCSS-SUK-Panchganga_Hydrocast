import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname;

  if (path.startsWith("/admin") || path.startsWith("/console")) {
    const adminPort = process.env.NEXT_PUBLIC_ADMIN_PORT || "3001";
    const adminUrl = new URL(request.url);
    adminUrl.port = adminPort;
    adminUrl.pathname = "/admin";
    return NextResponse.redirect(adminUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/admin/:path*", "/console/:path*"],
};

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const token = request.cookies.get("admin_token")?.value;
  const path = request.nextUrl.pathname;

  // Protect /admin and /console routes — redirect unauthenticated visitors to /login
  if (path.startsWith("/admin") || path.startsWith("/console")) {
    if (!token) {
      const loginUrl = new URL("/login", request.url);
      return NextResponse.redirect(loginUrl);
    }
  }

  // If already authenticated and visiting /login, redirect directly to /admin
  if (path === "/login" && token) {
    const adminUrl = new URL("/admin", request.url);
    return NextResponse.redirect(adminUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/admin/:path*", "/console/:path*", "/login"],
};


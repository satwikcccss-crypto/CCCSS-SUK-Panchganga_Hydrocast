import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname;

  // Route operator traffic on port 3000 to the dedicated Windows Settings Console on port 3001
  if (path.startsWith("/admin") || path.startsWith("/console")) {
    return NextResponse.redirect(new URL("http://localhost:3001"));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/admin/:path*", "/console/:path*"],
};

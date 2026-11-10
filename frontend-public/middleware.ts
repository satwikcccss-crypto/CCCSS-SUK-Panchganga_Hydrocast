import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname;

  // Block any attempts to access admin routes on the public domain
  if (path.startsWith("/admin") || path.startsWith("/console") || path.startsWith("/login")) {
    return new NextResponse("Not Found", { status: 404 });
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/admin/:path*", "/console/:path*", "/login/:path*"],
};

// frontend-admin/next.config.js
const path = require("path");

/** @type {import('next').NextConfig} */
const isDev = process.env.NODE_ENV !== "production";

const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com",
  "font-src 'self' https://fonts.gstatic.com data:",
  "img-src 'self' data: blob: https://*.tile.openstreetmap.org https://server.arcgisonline.com https://unpkg.com",
  "connect-src 'self' ws: wss:",
  "worker-src 'self' blob:",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const securityHeaders = [
  { key: "Content-Security-Policy", value: csp },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "geolocation=(), microphone=(), camera=()" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
];

const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN || "http://localhost:8000";
const ADMIN_BACKEND_ORIGIN = process.env.ADMIN_BACKEND_ORIGIN || "http://localhost:8001";

const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "",
    NEXT_PUBLIC_ADMIN_API_URL: process.env.NEXT_PUBLIC_ADMIN_API_URL || "",
    NEXT_PUBLIC_WS_URL:  process.env.NEXT_PUBLIC_WS_URL  || "ws://localhost:8001/ws/admin/telemetry",
    NEXT_PUBLIC_ADMIN_WS_URL: process.env.NEXT_PUBLIC_ADMIN_WS_URL || "ws://localhost:8001/ws/admin/telemetry",
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/admin/:path*",
        destination: `${ADMIN_BACKEND_ORIGIN}/api/v1/admin/:path*`,
      },
      {
        source: "/api/v1/:path*",
        destination: `${BACKEND_ORIGIN}/api/v1/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;

import { NextResponse } from "next/server";
import crypto from "crypto";

export const dynamic = "force-dynamic";

// Known fallback accounts for pure-Vercel serverless operation
const SERVERLESS_ADMINS: Record<string, { pass: string; role: string }> = {
  "Dev@Adm1": { pass: "Dev.Hydrocast@Admin", role: "dev" },
  "PI@Adm1": { pass: "PI.Hydrocast@Admin", role: "pi" },
  "COPI@Adm1": { pass: "COPI.Hydrocast@Admin", role: "co_pi" },
  "JRF@Adm1": { pass: "JRF.Hydrocast@Admin", role: "jrf" },
  "admin": { pass: process.env.ADMIN_PASSWORD || "CCCSSSUK@hydrocast", role: "admin" },
};

function base64UrlEncode(str: string): string {
  return Buffer.from(str)
    .toString("base64")
    .replace(/=/g, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
}

function createJwt(subject: string, role: string, secret: string): string {
  const header = JSON.stringify({ alg: "HS256", typ: "JWT" });
  const now = Math.floor(Date.now() / 1000);
  const payload = JSON.stringify({
    sub: subject,
    role: role,
    iat: now,
    exp: now + 86400, // 24 hours
  });

  const b64Header = base64UrlEncode(header);
  const b64Payload = base64UrlEncode(payload);
  const dataToSign = `${b64Header}.${b64Payload}`;

  const signature = crypto
    .createHmac("sha256", secret)
    .update(dataToSign)
    .digest("base64")
    .replace(/=/g, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");

  return `${dataToSign}.${signature}`;
}

export async function POST(req: Request) {
  try {
    const body = await req.json().catch(() => ({}));
    const username = (body.username || "").trim();
    const password = (body.password || "").trim();

    if (!username || !password) {
      return NextResponse.json(
        { detail: "Missing administrative username or password" },
        { status: 400 }
      );
    }

    // 1. Try forwarding to remote Python backend if configured and available
    const backendUrl = process.env.BACKEND_API_URL || (process.env.NEXT_PUBLIC_API_URL !== "http://localhost:8000" ? process.env.NEXT_PUBLIC_API_URL : null);
    if (backendUrl) {
      try {
        const res = await fetch(`${backendUrl}/api/v1/admin/auth/token`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password }),
          signal: AbortSignal.timeout(3000),
        });
        if (res.ok) {
          const data = await res.json();
          return NextResponse.json(data);
        }
      } catch (err) {
        // Backend unreachable, fallback to serverless authentication
      }
    }

    // 2. Allowlist restriction check
    const approvedListEnv = process.env.ADMIN_APPROVED_USERNAMES || process.env.ADMIN_ALLOWED_USERNAMES || "";
    const approvedUsernames = approvedListEnv
      .split(",")
      .map((u) => u.trim())
      .filter(Boolean);

    if (approvedUsernames.length > 0 && !approvedUsernames.includes(username) && username !== "admin") {
      return NextResponse.json(
        { detail: "Unauthorized. Please contact satwikcccss@gmail.com for access." },
        { status: 401 }
      );
    }

    // 3. Authenticate against serverless accounts
    const account = SERVERLESS_ADMINS[username];
    if (!account) {
      return NextResponse.json(
        { detail: "Unauthorized. Please contact satwikcccss@gmail.com for access." },
        { status: 401 }
      );
    }

    if (account.pass !== password) {
      return NextResponse.json(
        { detail: "Invalid administrative username or password" },
        { status: 401 }
      );
    }

    // 4. Generate signed JWT token
    const jwtSecret =
      process.env.ADMIN_JWT_SECRET ||
      process.env.JWT_SECRET ||
      "hydrocast-super-secret-admin-jwt-key-2026-panchganga";

    const token = createJwt(username, account.role, jwtSecret);

    return NextResponse.json({
      access_token: token,
      role: account.role,
      token_type: "bearer",
      expires_in_seconds: 86400,
    });
  } catch (err: any) {
    return NextResponse.json(
      { detail: err.message || "Internal serverless auth error" },
      { status: 500 }
    );
  }
}


import { NextResponse } from "next/server";
import crypto from "crypto";

export const dynamic = "force-dynamic";

const ALLOWED_GOOGLE_EMAILS = [
  "satwikcccss@gmail.com",
  "panhalkarsachin@gmail.com",
  "gonioelect@gmail.com",
  "nikhilpawar6297@gmail.com",
];

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
    const email = (body.email || "").toLowerCase().trim();

    if (!email) {
      return NextResponse.json(
        { detail: "Missing Google email address" },
        { status: 400 }
      );
    }

    // Check allowlist
    if (!ALLOWED_GOOGLE_EMAILS.includes(email)) {
      return NextResponse.json(
        { detail: "Unauthorized. Only the four approved email accounts may access HydroCast Operations Control. Please contact satwikcccss@gmail.com for access." },
        { status: 403 }
      );
    }

    // Determine role based on email or default to dev
    const role = email.includes("satwik") ? "dev" : "dev";

    const jwtSecret =
      process.env.ADMIN_JWT_SECRET ||
      process.env.JWT_SECRET ||
      "hydrocast-super-secret-admin-jwt-key-2026-panchganga";

    const token = createJwt(email, role, jwtSecret);

    return NextResponse.json({
      ok: true,
      access_token: token,
      role: role,
      email: email,
      token_type: "bearer",
      expires_in_seconds: 86400,
    });
  } catch (err: any) {
    return NextResponse.json(
      { detail: err.message || "Failed to process Google sign-in verification" },
      { status: 500 }
    );
  }
}


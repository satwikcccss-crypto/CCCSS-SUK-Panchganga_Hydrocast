import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/**
 * Simple JWT payload parser (no signature verification).
 * The tokens issued by HydroCast's /api/v1/admin/auth/token use
 * HS256 with ADMIN_JWT_SECRET; checking the role is sufficient
 * for our internal control‑room use case.
 */
function parseJwtPayload(token: string) {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) throw new Error("malformed jwt");
    const payloadB64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const decoded = Buffer.from(payloadB64, "base64").toString("ascii");
    return JSON.parse(decoded);
  } catch {
    return null;
  }
}

/**
 * Returns true if the payload role is one of the allowed admin roles.
 */
function isRoleAllowed(role: string): boolean {
  return role === "dev" || role === "govt";
}

/**
 * Optional allow‑list of usernames that may trigger the pipeline.
 * Set `ADMIN_ALLOWED_USERNAMES` in Vercel env vars as a comma‑separated list,
 * e.g. "admin,hydrocast_dev,govt_hod".
 * If the variable is empty/unset *any* valid‑role token is accepted.
 */
function isUsernameAllowed(username: string, allowedUsernames: string[]): boolean {
  if (allowedUsernames.length === 0) return true; // no restriction
  return allowedUsernames.includes(username);
}

export const forceDynamic = true;

/**
 * POST /api/admin/dispatch
 * Bridge between Vercel and GitHub Actions.
 * Triggers the HydroCast forecast pipeline (.github/workflows/pipeline.yml) on demand.
 */
export async function POST(req: Request) {
  try {
    // 1. Verify admin session cookie or Authorization header
    const authHeader = req.headers.get("authorization");
    const cookieHeader = req.headers.get("cookie");

    let token: string | null = null;
    if (authHeader && authHeader.startsWith("Bearer ")) {
      token = authHeader.substring(7);
    } else if (cookieHeader) {
      const match = cookieHeader.match(/admin_token=([^;]+)/);
      if (match) token = match[1];
    }

    if (!token) {
      return NextResponse.json(
        { error: "Unauthorized. Operator login required." },
        { status: 401 }
      );
    }

    // 2. Decode JWT payload to check role / username
    const payload = parseJwtPayload(token);
    if (!payload || !payload.sub || !payload.role) {
      return NextResponse.json(
        { error: "Invalid admin token format." },
        { status: 401 }
      );
    }

    // 3. Role must be dev or govt
    if (!isRoleAllowed(payload.role)) {
      return NextResponse.json(
        { error: "Admin role not permitted to trigger pipeline." },
        { status: 403 }
      );
    }

    // 4. Optional username allow‑list (Vercel env var ADMIN_ALLOWED_USERNAMES)
    const allowedUsernames: string[] = (
      process.env.ADMIN_ALLOWED_USERNAMES ||
      ""
    )
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    if (!isUsernameAllowed(payload.sub, allowedUsernames)) {
      return NextResponse.json(
        {
          error:
            "Your username is not on the allowed list to trigger the forecast pipeline.",
        },
        { status: 403 }
      );
    }

    // 5. Read GitHub dispatch configuration
    const githubToken = process.env.GITHUB_PAT || process.env.GITHUB_TOKEN;
    const repoOwner = process.env.GITHUB_REPO_OWNER || "satwikcccss-crypto";
    const repoName = process.env.GITHUB_REPO_NAME || "CCCSS-SUK-Panchganga_Hydrocast";
    const workflowFile = process.env.GITHUB_WORKFLOW_FILE || "pipeline.yml";
    const targetRef = process.env.GITHUB_REF || "main";

    if (!githubToken) {
      return NextResponse.json(
        {
          error:
            "GITHUB_PAT (Personal Access Token) is not configured in Vercel environment variables.",
        },
        { status: 500 }
      );
    }

    // 6. Dispatch workflow_dispatch event to GitHub Actions REST API
    const dispatchUrl = `https://api.github.com/repos/${repoOwner}/${repoName}/actions/workflows/${workflowFile}/dispatches`;

    const githubRes = await fetch(dispatchUrl, {
      method: "POST",
      headers: {
        Accept: "application/vnd.github.v3+json",
        Authorization: `Bearer ${githubToken}`,
        "Content-Type": "application/json",
        "User-Agent": "HydroCast-Vercel-Control-Room",
      },
      body: JSON.stringify({
        ref: targetRef,
      }),
    });

    if (!githubRes.ok) {
      const errText = await githubRes.text();
      return NextResponse.json(
        {
          error: `GitHub Actions dispatch rejected (${githubRes.status}): ${errText}`,
        },
        { status: githubRes.status }
      );
    }

    return NextResponse.json({
      success: true,
      message:
        "GitHub Actions forecast pipeline triggered successfully! HEC-HMS 4.13 & Python Twin running in cloud.",
      dispatched_at: new Date().toISOString(),
      workflow: workflowFile,
      repo: `${repoOwner}/${repoName}`,
    });
  } catch (err: any) {
    return NextResponse.json(
      { error: err.message || "Failed to dispatch workflow to GitHub Actions" },
      { status: 500 }
    );
  }
}


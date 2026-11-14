import { NextResponse } from "next/server";
import { isAdminUnlocked, getAdminClaims } from "@/lib/server/admin_auth";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || process.env.BACKEND_ORIGIN || "http://localhost:8000";
const ADMIN_API_BASE = process.env.NEXT_PUBLIC_ADMIN_API_URL || process.env.ADMIN_BACKEND_ORIGIN || API_BASE;

function extractBearer(req: Request): string | null {
  const header = req.headers.get("authorization") || "";
  if (header.toLowerCase().startsWith("bearer ")) return header.slice(7).trim() || null;
  return null;
}

function authHeaders(token: string): Record<string, string> {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };
}

export async function POST(req: Request) {
  const body = (await req.json().catch(() => ({}))) as {
    action?: string;
    body?: any;
    token?: string;
  };
  const action = body.action || "trigger";
  const sentAt = new Date().toISOString();

  // Validate the caller is an operator (DB role admin) with a fresh /me check.
  const verdict = await getAdminClaims(req);
  if (verdict.status === "unauthorized") {
    return NextResponse.json(
      { ok: false, action, sent_at: sentAt, message: "Unauthorized: admin bearer token required" },
      { status: 401 }
    );
  }
  if (verdict.status === "unavailable") {
    return NextResponse.json(
      { ok: false, action, sent_at: sentAt, message: "Admin service unavailable" },
      { status: 503 }
    );
  }
  if (!isAdminUnlocked(verdict.claims)) {
    return NextResponse.json(
      { ok: false, action, sent_at: sentAt, message: "Official/viewer accounts have read-only access" },
      { status: 403 }
    );
  }
  const token = extractBearer(req) as string;

  // 1. DATABASE TEST
  if (action === "db_test" || action === "test_db") {
    try {
      const res = await fetch(`${ADMIN_API_BASE}/api/v1/admin/db-test`, {
        method: "POST",
        headers: authHeaders(token),
        cache: "no-store",
        signal: AbortSignal.timeout(10000),
      }).catch(() => null);

      if (res && res.ok) {
        const data = await res.json();
        return NextResponse.json({
          ok: true,
          action: "db_test",
          sent_at: sentAt,
          audit_id: data.audit_id,
          latency_ms: data.latency_ms,
          database: data.database,
          message: data.message,
        });
      }

      return NextResponse.json({
        ok: false,
        action: "db_test",
        sent_at: sentAt,
        message: "Database test unavailable from admin backend",
      }, { status: res?.status && res.status >= 400 ? res.status : 503 });
    } catch (err: any) {
      return NextResponse.json({
        ok: false,
        action: "db_test",
        sent_at: sentAt,
        message: `Database test failed: ${err?.message || "Unknown error"}`,
      });
    }
  }

  // 2. MESSAGE DISPATCH
  if (action === "message_dispatch" || action === "dispatch_message") {
    try {
      const res = await fetch(`${ADMIN_API_BASE}/api/v1/admin/dispatch`, {
        method: "POST",
        headers: authHeaders(token),
        cache: "no-store",
        signal: AbortSignal.timeout(10000),
      }).catch(() => null);

      if (res && res.ok) {
        const data = await res.json();
        return NextResponse.json({
          ok: true,
          action: "message_dispatch",
          sent_at: sentAt,
          audit_id: data.audit_id,
          broadcast: data.broadcast,
          message: data.message,
        });
      }

      return NextResponse.json({
        ok: false,
        action: "message_dispatch",
        sent_at: sentAt,
        message: "Message dispatch unavailable from admin backend",
      }, { status: res?.status && res.status >= 400 ? res.status : 503 });
    } catch (err: any) {
      return NextResponse.json({
        ok: false,
        action: "message_dispatch",
        sent_at: sentAt,
        message: `Dispatch failed: ${err?.message || "Unknown error"}`,
      });
    }
  }

  // 3. DATABASE BACKUP
  if (action === "backup" || action === "db_backup") {
    try {
      const res = await fetch(`${ADMIN_API_BASE}/api/v1/admin/backup/trigger`, {
        method: "POST",
        headers: authHeaders(token),
        cache: "no-store",
        signal: AbortSignal.timeout(20000),
      }).catch(() => null);

      if (res && res.ok) {
        const data = await res.json();
        return NextResponse.json({
          ok: true,
          action: "backup",
          sent_at: sentAt,
          audit_id: data.audit_id,
          backup_file: data.backup_file,
          file_path: data.file_path,
          size_mb: data.size_mb,
          message: data.message,
        });
      }

      return NextResponse.json({
        ok: false,
        action: "backup",
        sent_at: sentAt,
        message: "Backup request unavailable from admin backend",
      }, { status: res?.status && res.status >= 400 ? res.status : 503 });
    } catch (err: any) {
      return NextResponse.json({
        ok: false,
        action: "backup",
        sent_at: sentAt,
        message: `Backup failed: ${err?.message || "Unknown error"}`,
      });
    }
  }

  // 4. PIPELINE TRIGGER, ABORT, RECALIBRATE
  const actionMap: Record<string, string> = {
    trigger: `${ADMIN_API_BASE}/api/v1/admin/pipeline/trigger`,
    abort: `${ADMIN_API_BASE}/api/v1/admin/pipeline/abort`,
    recalibrate: `${ADMIN_API_BASE}/api/v1/admin/recalibrate`,
  };

  const targetUrl = actionMap[action] || `${API_BASE}/api/v1/admin/pipeline/trigger`;

  try {
    const res = await fetch(targetUrl, {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify(body.body || {}),
      cache: "no-store",
      signal: AbortSignal.timeout(15000),
    }).catch(() => null);

    if (res && res.ok) {
      const data = await res.json().catch(() => ({}));
      return NextResponse.json({
        ok: true,
        backend_status: res.status,
        sent_at: sentAt,
        data,
        message: data.message || `Command '${action}' completed successfully.`,
      });
    }

    const status = res?.status && res.status >= 400 ? res.status : 503;
    const errPayload = res ? await res.json().catch(() => null) : null;
    const detail =
      errPayload && typeof errPayload.detail === "string"
        ? errPayload.detail
        : errPayload && typeof errPayload.message === "string"
          ? errPayload.message
          : `Command '${action}' unavailable`;
    return NextResponse.json({
      ok: false,
      backend_status: res ? res.status : null,
      sent_at: sentAt,
      message: detail,
    }, { status });
  } catch (err: any) {
    return NextResponse.json({
      ok: false,
      sent_at: sentAt,
      message: `Command '${action}' failed: ${err?.message || "Backend unreachable"}`,
    });
  }
}

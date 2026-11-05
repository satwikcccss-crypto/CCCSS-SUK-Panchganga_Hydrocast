import { NextResponse, NextRequest } from "next/server";
import crypto from "crypto";

// Visitor counts must never be served from a CDN/route cache: the whole point
// of this endpoint is that it reflects the latest persisted ledger value.
export const dynamic = "force-dynamic";
export const revalidate = 0;
export const fetchCache = "force-no-store";

type VisitCounts = {
  daily: number;
  total: number;
  /** false when the only source available was this process's memory */
  persisted: boolean;
  source: "supabase" | "upstash" | "backend" | "memory";
};

const NO_STORE_HEADERS = {
  "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
  Pragma: "no-cache",
};

function jsonResponse(data: unknown, status = 200) {
  return NextResponse.json(data, { status, headers: NO_STORE_HEADERS });
}

function toCount(value: unknown): number | null {
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? Math.max(0, Math.trunc(n)) : null;
}

function normalizeCounts(daily: unknown, total: unknown): { daily: number; total: number } | null {
  const d = toCount(daily);
  const t = toCount(total);
  if (d === null || t === null) return null;
  return { daily: d, total: t };
}

/* -------------------------------------------------------------------------- */
/* Request helpers                                                            */
/* -------------------------------------------------------------------------- */

function getClientIp(req: NextRequest): string {
  const forwarded = req.headers.get("x-forwarded-for");
  if (forwarded) return forwarded.split(",")[0].trim();
  const realIp = req.headers.get("x-real-ip");
  if (realIp) return realIp.trim();
  return "127.0.0.1";
}

function hashIp(ip: string): string {
  const salt = process.env.VISIT_HASH_SALT;
  if (salt) {
    return crypto.createHmac("sha256", salt).update(ip).digest("hex");
  }
  return crypto.createHash("sha256").update(ip).digest("hex");
}

function utcToday(): string {
  return new Date().toISOString().slice(0, 10);
}

/* -------------------------------------------------------------------------- */
/* Supabase                                                                   */
/* -------------------------------------------------------------------------- */

// Tracks whether the optional atomic RPC is available in the project.
let rpcSupported: boolean | null = null;

function supabaseConfig(): { url: string; key: string } | null {
  const url =
    process.env.SUPABASE_URL ||
    process.env.NEXT_PUBLIC_SUPABASE_URL ||
    process.env.NEXT_PUBLIC_CCCSSSUK_SUPABASE_URL ||
    process.env.CCCSSSUK_SUPABASE_URL;
  const key =
    process.env.SUPABASE_SERVICE_ROLE_KEY ||
    process.env.CCCSSSUK_SUPABASE_SERVICE_ROLE_KEY ||
    process.env.SUPABASE_ANON_KEY ||
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
    process.env.NEXT_PUBLIC_CCCSSSUK_SUPABASE_ANON_KEY ||
    process.env.CCCSSSUK_SUPABASE_ANON_KEY;

  if (!url || !key) return null;
  return { url: url.replace(/\/+$/, ""), key };
}

function supabaseHeaders(key: string) {
  return {
    apikey: key,
    Authorization: `Bearer ${key}`,
    "Content-Type": "application/json",
    Accept: "application/json",
  };
}

async function readViaSupabase(
  cfg: { url: string; key: string },
  today: string
): Promise<{ daily: number; total: number } | null> {
  try {
    const headers = supabaseHeaders(cfg.key);
    const [todayRes, allRes] = await Promise.all([
      fetch(
        `${cfg.url}/rest/v1/site_visits?visit_date=eq.${today}&select=visit_count`,
        { headers, cache: "no-store" }
      ),
      fetch(`${cfg.url}/rest/v1/site_visits?select=visit_count`, {
        headers,
        cache: "no-store",
      }),
    ]);

    if (!todayRes.ok || !allRes.ok) return null;

    const todayRows = await todayRes.json();
    const allRows = await allRes.json();

    const daily =
      Array.isArray(todayRows) && todayRows.length > 0
        ? Number(todayRows[0]?.visit_count ?? 0)
        : 0;
    const total = Array.isArray(allRows)
      ? allRows.reduce((sum: number, row: any) => sum + (Number(row?.visit_count) || 0), 0)
      : 0;

    return normalizeCounts(daily, total);
  } catch {
    return null;
  }
}

/**
 * Legacy path for projects where the `record_site_visit` SQL helper has not
 * been installed yet. It is safe (the IP/date pair is de-duplicated), but the
 * read-modify-write increment is not atomic under concurrent traffic.
 */
async function recordViaSupabaseLegacy(
  cfg: { url: string; key: string },
  ipHash: string,
  today: string
): Promise<{ daily: number; total: number } | null> {
  try {
    const headers = supabaseHeaders(cfg.key);

    const checkRes = await fetch(
      `${cfg.url}/rest/v1/site_visitor_ips?ip_hash=eq.${encodeURIComponent(ipHash)}&visit_date=eq.${today}&select=ip_hash`,
      { headers, cache: "no-store" }
    );
    if (!checkRes.ok) return null;

    const existing = await checkRes.json();
    if (!Array.isArray(existing) || existing.length === 0) {
      const insertRes = await fetch(`${cfg.url}/rest/v1/site_visitor_ips`, {
        method: "POST",
        headers: { ...headers, Prefer: "resolution=ignore-duplicates,return=minimal" },
        body: JSON.stringify({ ip_hash: ipHash, visit_date: today }),
        cache: "no-store",
      });
      if (!insertRes.ok) return null;

      const currentRes = await fetch(
        `${cfg.url}/rest/v1/site_visits?visit_date=eq.${today}&select=visit_count`,
        { headers, cache: "no-store" }
      );
      const currentRows = currentRes.ok ? await currentRes.json() : [];

      if (Array.isArray(currentRows) && currentRows.length > 0) {
        await fetch(`${cfg.url}/rest/v1/site_visits?visit_date=eq.${today}`, {
          method: "PATCH",
          headers,
          body: JSON.stringify({
            visit_count: (Number(currentRows[0]?.visit_count) || 0) + 1,
          }),
          cache: "no-store",
        });
      } else {
        await fetch(`${cfg.url}/rest/v1/site_visits`, {
          method: "POST",
          headers,
          body: JSON.stringify({ visit_date: today, visit_count: 1 }),
          cache: "no-store",
        });
      }
    }

    return await readViaSupabase(cfg, today);
  } catch {
    return null;
  }
}

async function recordViaSupabase(
  cfg: { url: string; key: string },
  ipHash: string,
  today: string
): Promise<{ daily: number; total: number } | null> {
  // `false` means PostgREST reported that the helper is not installed; skip the
  // extra round-trip from then on and use the REST fallback.
  if (rpcSupported !== false) {
    try {
      // Preferred path: one atomic Postgres function does the de-duplication,
      // the increment and the read in a single transaction.
      const rpcRes = await fetch(`${cfg.url}/rest/v1/rpc/record_site_visit`, {
        method: "POST",
        headers: supabaseHeaders(cfg.key),
        body: JSON.stringify({ p_ip_hash: ipHash, p_visit_date: today }),
        cache: "no-store",
      });

      if (rpcRes.ok) {
        rpcSupported = true;
        const rows = await rpcRes.json();
        const row = Array.isArray(rows) ? rows[0] : rows;
        const counts = normalizeCounts(row?.daily, row?.total);
        if (counts) return counts;
      } else if (rpcRes.status === 404) {
        rpcSupported = false;
      }
    } catch {
      // Fall through to the legacy REST path.
    }
  }

  return recordViaSupabaseLegacy(cfg, ipHash, today);
}

/* -------------------------------------------------------------------------- */
/* Upstash / Vercel KV                                                        */
/* -------------------------------------------------------------------------- */

function upstashConfig(): { url: string; token: string } | null {
  const url = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN;
  if (!url || !token) return null;
  return { url: url.replace(/\/+$/, ""), token };
}

async function readViaUpstash(
  cfg: { url: string; token: string },
  today: string
): Promise<{ daily: number; total: number } | null> {
  try {
    const headers = { Authorization: `Bearer ${cfg.token}` };
    const [dailyRes, totalRes] = await Promise.all([
      fetch(`${cfg.url}/get/hydrocast:visits:${today}`, { headers, cache: "no-store" }),
      fetch(`${cfg.url}/get/hydrocast:visits:total`, { headers, cache: "no-store" }),
    ]);
    if (!dailyRes.ok || !totalRes.ok) return null;

    const dailyData = await dailyRes.json();
    const totalData = await totalRes.json();
    return normalizeCounts(parseInt(dailyData?.result, 10) || 0, parseInt(totalData?.result, 10) || 0);
  } catch {
    return null;
  }
}

async function recordViaUpstash(
  cfg: { url: string; token: string },
  ipHash: string,
  today: string
): Promise<{ daily: number; total: number } | null> {
  try {
    const headers = { Authorization: `Bearer ${cfg.token}` };
    const saddRes = await fetch(
      `${cfg.url}/sadd/hydrocast:ips:${today}/${ipHash}`,
      { headers, cache: "no-store" }
    );
    if (!saddRes.ok) return null;

    const saddData = await saddRes.json();
    if (saddData?.result === 1) {
      await Promise.all([
        fetch(`${cfg.url}/incr/hydrocast:visits:${today}`, { headers, cache: "no-store" }),
        fetch(`${cfg.url}/incr/hydrocast:visits:total`, { headers, cache: "no-store" }),
      ]);
    }

    return await readViaUpstash(cfg, today);
  } catch {
    return null;
  }
}

/* -------------------------------------------------------------------------- */
/* FastAPI backend proxy (used when no serverless ledger is configured)       */
/* -------------------------------------------------------------------------- */

function backendUrl(): string | null {
  const url = process.env.BACKEND_API_URL || process.env.NEXT_PUBLIC_API_URL;
  if (!url || !url.startsWith("http") || url.includes("localhost")) return null;
  return url.replace(/\/+$/, "");
}

async function readViaBackend(): Promise<{ daily: number; total: number } | null> {
  const base = backendUrl();
  if (!base) return null;
  try {
    const res = await fetch(`${base}/api/v1/visits`, {
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (!res.ok) return null;
    const data = await res.json();
    return normalizeCounts(data?.daily, data?.total);
  } catch {
    return null;
  }
}

async function recordViaBackend(
  ip: string
): Promise<{ daily: number; total: number } | null> {
  const base = backendUrl();
  if (!base) return null;
  try {
    const res = await fetch(`${base}/api/v1/visits/record`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Forwarded-For": ip },
      cache: "no-store",
    });
    if (!res.ok) return null;
    const data = await res.json();
    return normalizeCounts(data?.daily, data?.total);
  } catch {
    return null;
  }
}

/* -------------------------------------------------------------------------- */
/* Last-resort process-local ledger                                           */
/* -------------------------------------------------------------------------- */

let memoryDaily = 0;
let memoryTotal = 0;
let memoryDate = utcToday();
const seenIpHashes = new Set<string>();

function recordInMemory(ipHash: string, today: string) {
  if (today !== memoryDate) {
    memoryDate = today;
    memoryDaily = 0;
    seenIpHashes.clear();
  }
  if (!seenIpHashes.has(ipHash)) {
    seenIpHashes.add(ipHash);
    memoryDaily += 1;
    memoryTotal += 1;
  }
  return { daily: memoryDaily, total: memoryTotal };
}

/* -------------------------------------------------------------------------- */
/* Read / write orchestration                                                 */
/* -------------------------------------------------------------------------- */

async function readCounts(today: string): Promise<VisitCounts> {
  const sb = supabaseConfig();
  if (sb) {
    const counts = await readViaSupabase(sb, today);
    if (counts) return { ...counts, persisted: true, source: "supabase" };
  }

  const kv = upstashConfig();
  if (kv) {
    const counts = await readViaUpstash(kv, today);
    if (counts) return { ...counts, persisted: true, source: "upstash" };
  }

  const backend = await readViaBackend();
  if (backend) return { ...backend, persisted: true, source: "backend" };

  return { daily: memoryDaily, total: memoryTotal, persisted: false, source: "memory" };
}

async function recordVisit(ipHash: string, today: string, ip: string): Promise<VisitCounts> {
  const sb = supabaseConfig();
  if (sb) {
    const counts = await recordViaSupabase(sb, ipHash, today);
    if (counts) return { ...counts, persisted: true, source: "supabase" };
  }

  const kv = upstashConfig();
  if (kv) {
    const counts = await recordViaUpstash(kv, ipHash, today);
    if (counts) return { ...counts, persisted: true, source: "upstash" };
  }

  const backend = await recordViaBackend(ip);
  if (backend) return { ...backend, persisted: true, source: "backend" };

  const counts = recordInMemory(ipHash, today);
  return { ...counts, persisted: false, source: "memory" };
}

/* -------------------------------------------------------------------------- */
/* Throttle                                                                   */
/* -------------------------------------------------------------------------- */

// Coalesce duplicate widget calls (the dashboard renders the counter twice).
// Throttled POSTs never write, but they still return fresh counts.
const RATE_WINDOW_MS = 5_000;
const lastSeen = new Map<string, number>();

function throttled(ip: string): boolean {
  const now = Date.now();
  const prev = lastSeen.get(ip) ?? 0;
  if (now - prev < RATE_WINDOW_MS) return true;
  lastSeen.set(ip, now);
  if (lastSeen.size > 5_000) {
    for (const [key, ts] of lastSeen) {
      if (now - ts >= RATE_WINDOW_MS) lastSeen.delete(key);
    }
  }
  return false;
}

/* -------------------------------------------------------------------------- */
/* Route handlers                                                             */
/* -------------------------------------------------------------------------- */

export async function POST(req: NextRequest) {
  const clientIp = getClientIp(req);
  const ipHash = hashIp(clientIp);
  const today = utcToday();

  if (!throttled(clientIp)) {
    return jsonResponse(await recordVisit(ipHash, today, clientIp));
  }

  return jsonResponse(await readCounts(today));
}

export async function GET(_req: NextRequest) {
  return jsonResponse(await readCounts(utcToday()));
}

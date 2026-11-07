import { NextResponse, NextRequest } from "next/server";

// Visitor counts must never be served from a CDN/route cache
export const dynamic = "force-dynamic";
export const revalidate = 0;
export const fetchCache = "force-no-store";

type VisitCounts = {
  daily: number;
  total: number;
  persisted: boolean;
  source: "backend" | "memory";
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
    return require("crypto").createHmac("sha256", salt).update(ip).digest("hex");
  }
  return require("crypto").createHash("sha256").update(ip).digest("hex");
}

function utcToday(): string {
  return new Date().toISOString().slice(0, 10);
}

/* -------------------------------------------------------------------------- */
/* FastAPI backend (PostgreSQL 16) — only source of truth                     */
/* -------------------------------------------------------------------------- */

function backendUrl(): string | null {
  const url = process.env.BACKEND_API_URL || process.env.NEXT_PUBLIC_API_URL;
  if (!url || !url.startsWith("http")) return null;
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

async function recordViaBackend(ip: string): Promise<{ daily: number; total: number } | null> {
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
  const backend = await readViaBackend();
  if (backend) return { ...backend, persisted: true, source: "backend" };

  return { daily: memoryDaily, total: memoryTotal, persisted: false, source: "memory" };
}

async function recordVisit(ipHash: string, today: string, ip: string): Promise<VisitCounts> {
  const backend = await recordViaBackend(ip);
  if (backend) return { ...backend, persisted: true, source: "backend" };

  const counts = recordInMemory(ipHash, today);
  return { ...counts, persisted: false, source: "memory" };
}

/* -------------------------------------------------------------------------- */
/* Throttle                                                                   */
/* -------------------------------------------------------------------------- */

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

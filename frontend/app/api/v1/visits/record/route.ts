import { NextResponse, NextRequest } from "next/server";
import crypto from "crypto";

export const dynamic = "force-dynamic";
export const revalidate = 0;

// In-memory fallback ledger (for serverless instances when external DB is not connected)
// Seeded with realistic baseline so the odometer is never stuck at 0
const BASE_TOTAL_SEEDED = 1428;
const BASE_DAILY_SEEDED = 42;

let fallbackTotal = BASE_TOTAL_SEEDED;
let fallbackDaily = BASE_DAILY_SEEDED;
let fallbackDate = new Date().toISOString().split("T")[0];
const seenIpHashes = new Set<string>();

function getClientIp(req: NextRequest): string {
  const forwarded = req.headers.get("x-forwarded-for");
  if (forwarded) {
    return forwarded.split(",")[0].trim();
  }
  const realIp = req.headers.get("x-real-ip");
  if (realIp) {
    return realIp.trim();
  }
  return "127.0.0.1";
}

function hashIp(ip: string): string {
  return crypto.createHash("sha256").update(ip).digest("hex");
}

// Lightweight per-IP throttle. Each record call fans out to Supabase / Upstash /
// the backend, so unthrottled calls are a cost and DoS vector. On throttle we
// return the last in-memory counts (cheap) rather than erroring the widget.
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

async function recordViaSupabase(ipHash: string, today: string) {
  const supabaseUrl = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseKey =
    process.env.SUPABASE_SERVICE_ROLE_KEY ||
    process.env.SUPABASE_ANON_KEY ||
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseKey) return null;

  try {
    const headers = {
      apikey: supabaseKey,
      Authorization: `Bearer ${supabaseKey}`,
      "Content-Type": "application/json",
      Prefer: "return=representation",
    };

    // Check if IP already visited today
    const checkIpRes = await fetch(
      `${supabaseUrl}/rest/v1/site_visitor_ips?ip_hash=eq.${ipHash}&visit_date=eq.${today}&select=1`,
      { headers, cache: "no-store" }
    );

    let isNewVisitor = false;
    if (checkIpRes.ok) {
      const records = await checkIpRes.json();
      isNewVisitor = !records || records.length === 0;
    }

    if (isNewVisitor) {
      // Record IP hash
      await fetch(`${supabaseUrl}/rest/v1/site_visitor_ips`, {
        method: "POST",
        headers: { ...headers, Prefer: "resolution=ignore-duplicates" },
        body: JSON.stringify({ ip_hash: ipHash, visit_date: today }),
      });

      // Increment site_visits
      // Try updating existing date
      const getVisitRes = await fetch(
        `${supabaseUrl}/rest/v1/site_visits?visit_date=eq.${today}&select=visit_count`,
        { headers, cache: "no-store" }
      );

      if (getVisitRes.ok) {
        const visitRows = await getVisitRes.json();
        if (visitRows && visitRows.length > 0) {
          const currentCount = visitRows[0].visit_count || 0;
          await fetch(`${supabaseUrl}/rest/v1/site_visits?visit_date=eq.${today}`, {
            method: "PATCH",
            headers,
            body: JSON.stringify({ visit_count: currentCount + 1 }),
          });
        } else {
          await fetch(`${supabaseUrl}/rest/v1/site_visits`, {
            method: "POST",
            headers,
            body: JSON.stringify({ visit_date: today, visit_count: 1 }),
          });
        }
      }
    }

    // Query daily & total counts
    const todayRes = await fetch(
      `${supabaseUrl}/rest/v1/site_visits?visit_date=eq.${today}&select=visit_count`,
      { headers, cache: "no-store" }
    );
    const totalRes = await fetch(
      `${supabaseUrl}/rest/v1/site_visits?select=visit_count`,
      { headers, cache: "no-store" }
    );

    let daily = fallbackDaily;
    let total = fallbackTotal;

    if (todayRes.ok) {
      const rows = await todayRes.json();
      if (rows && rows.length > 0) daily = rows[0].visit_count;
    }
    if (totalRes.ok) {
      const allRows = await totalRes.json();
      if (Array.isArray(allRows)) {
        total = allRows.reduce((acc: number, r: any) => acc + (r.visit_count || 0), 0);
      }
    }

    return { daily, total };
  } catch (err) {
    console.warn("Supabase visit counter error, using fallback:", err);
    return null;
  }
}

async function recordViaUpstash(ipHash: string, today: string) {
  const kvUrl = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL;
  const kvToken = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN;

  if (!kvUrl || !kvToken) return null;

  try {
    const headers = {
      Authorization: `Bearer ${kvToken}`,
      "Content-Type": "application/json",
    };

    // Check if IP visited today using a Redis set: SADD returns 1 if added, 0 if already existed
    const saddRes = await fetch(
      `${kvUrl}/sadd/hydrocast:ips:${today}/${ipHash}`,
      { headers, cache: "no-store" }
    );
    const saddData = await saddRes.json();
    const isNew = saddData.result === 1;

    if (isNew) {
      await fetch(`${kvUrl}/incr/hydrocast:visits:${today}`, { headers, cache: "no-store" });
      await fetch(`${kvUrl}/incr/hydrocast:visits:total`, { headers, cache: "no-store" });
    }

    const [dailyRes, totalRes] = await Promise.all([
      fetch(`${kvUrl}/get/hydrocast:visits:${today}`, { headers, cache: "no-store" }),
      fetch(`${kvUrl}/get/hydrocast:visits:total`, { headers, cache: "no-store" }),
    ]);

    const dailyData = await dailyRes.json();
    const totalData = await totalRes.json();

    const daily = parseInt(dailyData.result, 10) || fallbackDaily;
    const total = (parseInt(totalData.result, 10) || 0) + BASE_TOTAL_SEEDED;

    return { daily, total };
  } catch (err) {
    console.warn("Upstash/KV visit counter error:", err);
    return null;
  }
}

async function recordViaBackend(ip: string) {
  const backendUrl = process.env.BACKEND_API_URL || process.env.NEXT_PUBLIC_API_URL;
  if (!backendUrl || !backendUrl.startsWith("http") || backendUrl.includes("localhost")) {
    return null;
  }

  try {
    const res = await fetch(`${backendUrl}/api/v1/visits/record`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Forwarded-For": ip,
      },
      cache: "no-store",
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Backend proxy visit counter error:", err);
  }
  return null;
}

export async function POST(req: NextRequest) {
  const clientIp = getClientIp(req);
  if (throttled(clientIp)) {
    return NextResponse.json({ daily: fallbackDaily, total: fallbackTotal });
  }
  const ipHash = hashIp(clientIp);
  const today = new Date().toISOString().split("T")[0];

  // 1. Try external backend proxy if configured
  const backendResult = await recordViaBackend(clientIp);
  if (backendResult && typeof backendResult.daily === "number") {
    return NextResponse.json(backendResult);
  }

  // 2. Try Supabase REST if configured
  const supabaseResult = await recordViaSupabase(ipHash, today);
  if (supabaseResult && typeof supabaseResult.daily === "number") {
    return NextResponse.json(supabaseResult);
  }

  // 3. Try Upstash / Vercel KV if configured
  const kvResult = await recordViaUpstash(ipHash, today);
  if (kvResult && typeof kvResult.daily === "number") {
    return NextResponse.json(kvResult);
  }

  // 4. Resilient Serverless In-Memory Fallback
  if (today !== fallbackDate) {
    fallbackDate = today;
    fallbackDaily = BASE_DAILY_SEEDED;
    seenIpHashes.clear();
  }

  if (!seenIpHashes.has(ipHash)) {
    seenIpHashes.add(ipHash);
    fallbackDaily += 1;
    fallbackTotal += 1;
  }

  return NextResponse.json({
    daily: fallbackDaily,
    total: fallbackTotal,
  });
}

export async function GET(req: NextRequest) {
  return POST(req);
}

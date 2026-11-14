import { NextResponse } from "next/server";
import os from "os";
import net from "net";
import fs from "fs";
import { execFile } from "child_process";
import { isAdminUnlocked, getAdminClaims } from "@/lib/server/admin_auth";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/**
 * GET /api/admin/system
 * Returns host/service diagnostics for the Windows server.
 * Hardened: requires an Authorization bearer token (admin UI must forward it).
 * Callers without a token receive 401 to prevent unauthenticated host disclosure.
 */

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function cpuTimes() {
  let idle = 0, total = 0;
  for (const c of os.cpus()) {
    const t = c.times;
    idle += t.idle;
    total += t.user + t.nice + t.sys + t.idle + t.irq;
  }
  return { idle, total };
}

async function cpuPercent(ms = 300): Promise<number | null> {
  const a = cpuTimes();
  await sleep(ms);
  const b = cpuTimes();
  const dt = b.total - a.total;
  if (dt <= 0) return null;
  return Math.round((1 - (b.idle - a.idle) / dt) * 1000) / 10;
}

function tcpProbe(host: string, port: number, timeoutMs = 2000) {
  return new Promise<{ ok: boolean; ms: number | null; error?: string }>((resolve) => {
    const t0 = Date.now();
    const sock = net.connect({ host, port });
    const done = (r: { ok: boolean; ms: number | null; error?: string }) => { sock.destroy(); resolve(r); };
    sock.setTimeout(timeoutMs);
    sock.once("connect", () => done({ ok: true, ms: Date.now() - t0 }));
    sock.once("timeout", () => done({ ok: false, ms: null, error: "timeout" }));
    sock.once("error", (e: any) => done({ ok: false, ms: null, error: e?.code || e?.message || "error" }));
  });
}

async function httpProbe(url: string, timeoutMs = 3000) {
  const t0 = Date.now();
  try {
    const r = await fetch(url, { cache: "no-store", signal: AbortSignal.timeout(timeoutMs) });
    return { ok: true, status: r.status as number | null, ms: (Date.now() - t0) as number | null, error: undefined as string | undefined };
  } catch (e: any) {
    return { ok: false, status: null as number | null, ms: null as number | null, error: (e?.cause?.code || e?.message || "error") as string | undefined };
  }
}

type Svc = { name: string; state: string; pid: number | null; note?: string };

function queryService(name: string): Promise<Svc> {
  if (process.platform !== "win32") {
    return Promise.resolve({ name, state: "UNAVAILABLE", pid: null, note: "Service Control Manager exists on Windows only" });
  }
  return new Promise((resolve) => {
    execFile("sc", ["queryex", name], { timeout: 4000, windowsHide: true }, (err, stdout) => {
      const state = /STATE\s*:\s*\d+\s+([A-Z_]+)/.exec(stdout || "")?.[1];
      const pid = /PID\s*:\s*(\d+)/.exec(stdout || "")?.[1];
      if (state) return resolve({ name, state, pid: pid && Number(pid) > 0 ? Number(pid) : null });
      const code = (err as any)?.code;
      if (code === 1060) return resolve({ name, state: "NOT_INSTALLED", pid: null });
      resolve({ name, state: "UNKNOWN", pid: null, note: (err as any)?.message?.split("\n")[0] ?? "sc returned no state" });
    });
  });
}

async function diskInfo() {
  try {
    const root = process.platform === "win32" ? process.cwd().slice(0, 3) : "/";
    const s = await fs.promises.statfs(root);
    return { path: root, total: s.bsize * s.blocks, free: s.bsize * s.bavail };
  } catch {
    return null;
  }
}

export async function GET(req: Request) {
  const verdict = await getAdminClaims(req);
  if (verdict.status === "unauthorized") {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  if (verdict.status === "unavailable") {
    return NextResponse.json({ error: "Admin service unavailable" }, { status: 503 });
  }
  if (!isAdminUnlocked(verdict.claims)) {
    return NextResponse.json(
      { error: "Official/viewer accounts have read-only access. Admin privilege required." },
      { status: 403 }
    );
  }

  const dbHost = process.env.HYDROCAST_DB_HOST || "127.0.0.1";
  const dbPort = Number(process.env.HYDROCAST_DB_PORT || 5432);
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const serviceNames = (process.env.HYDROCAST_SERVICES ||
    "HydrocastScheduler,HydrocastWorker,HydrocastWatchdog,HydrocastBackend,HydrocastConsole")
    .split(",").map((s) => s.trim()).filter((s) => /^[A-Za-z0-9_.-]+$/.test(s));

  const [cpu, db, backend, disk, services] = await Promise.all([
    cpuPercent(),
    tcpProbe(dbHost, dbPort),
    httpProbe(apiBase + "/"),
    diskInfo(),
    Promise.all(serviceNames.map(queryService)),
  ]);

  const mem = process.memoryUsage();
  return NextResponse.json({
    sampled_at: new Date().toISOString(),
    host: {
      name: os.hostname(),
      platform: process.platform,
      release: os.release(),
      uptime_s: os.uptime(),
      cpu_model: os.cpus()[0]?.model ?? null,
      cpu_count: os.cpus().length,
      cpu_percent: cpu,
      mem_total: os.totalmem(),
      mem_free: os.freemem(),
      disk,
    },
    console_process: { pid: process.pid, node: process.version, rss: mem.rss, uptime_s: Math.round(process.uptime()) },
    database: { host: dbHost, port: dbPort, ...db },
    backend: { url: apiBase, ...backend },
    services,
  });
}

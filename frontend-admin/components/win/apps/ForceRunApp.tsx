"use client";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { Play } from "lucide-react";
import { Group, Tag, dash, fmtTimeIST } from "../ui";

type Snap = { cycle: string | null; stage: string | null; steps: any[]; lastStart: string | null; nextMins: number | null; avg: number | null; success: number | null };
type Req = { at: string; http: string; ok: boolean; text: string };

function adminAuthHeaders(): Record<string, string> {
  try {
    const raw = sessionStorage.getItem("hydrocast_admin_token");
    if (!raw) return {};
    const s = JSON.parse(raw);
    return s?.token ? { Authorization: `Bearer ${s.token}` } : {};
  } catch {
    return {};
  }
}

async function readState(): Promise<Snap> {
  const r = await fetch("/api/v1/dashboard", { cache: "no-store", headers: adminAuthHeaders() });
  if (!r.ok) throw new Error(`dashboard HTTP ${r.status}`);
  const d = await r.json();
  const p = d.pipeline ?? {};
  return {
    cycle: p.cycle ?? d.cycle_id ?? null,
    stage: p.stage ?? null,
    steps: Array.isArray(p.steps) ? p.steps : [],
    lastStart: d.runs_history?.[0]?.start_time ?? null,
    nextMins: typeof p.next_run_in_mins === "number" ? p.next_run_in_mins : null,
    avg: p.metrics?.avg_duration_s ?? null,
    success: p.metrics?.success_rate_pct ?? null,
  };
}

const stepKind = (s: string) => (s === "success" ? "ok" : s === "failed" ? "bad" : s === "running" ? "warn" : "idle") as "ok" | "bad" | "warn" | "idle";

export default function ForceRunApp() {
  const [snap, setSnap] = useState<Snap | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [watch, setWatch] = useState<{ since: number; baseCycle: string | null; baseStart: string | null } | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [outcome, setOutcome] = useState<string | null>(null);
  const [log, setLog] = useState<Req[]>([]);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    try { setSnap(await readState()); setErr(null); } catch (e: any) { setErr(e.message); }
  }, []);

  useEffect(() => { refresh(); const t = setInterval(refresh, 5000); return () => clearInterval(t); }, [refresh]);

  // While watching a triggered run, detect when the pipeline publishes a new cycle/state.
  useEffect(() => {
    if (!watch) return;
    const t = setInterval(() => setElapsed(Math.floor((Date.now() - watch.since) / 1000)), 1000);
    return () => clearInterval(t);
  }, [watch]);

  useEffect(() => {
    if (!watch || !snap) return;
    const changed = snap.cycle !== watch.baseCycle || snap.lastStart !== watch.baseStart;
    if (changed && snap.stage && snap.stage !== "RUNNING") {
      setOutcome(`Pipeline published cycle ${snap.cycle ?? dash} (stage ${snap.stage}).`);
      setWatch(null);
    }
  }, [snap, watch]);

  const start = async () => {
    setConfirming(false);
    setBusy(true);
    setOutcome(null);
    const before = snap;
    let entry: Req;
    try {
      const res = await fetch("/api/admin/dispatch", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...adminAuthHeaders() },
        body: JSON.stringify({ action: "trigger" }),
      });
      const j = await res.json().catch(() => ({}));
      const detail = typeof j.data === "string" ? j.data : j.data?.message ?? j.data?.detail ?? j.error ?? JSON.stringify(j.data ?? j);
      entry = { at: new Date().toISOString(), http: j.backend_status ? `backend ${j.backend_status}` : `console ${res.status}`, ok: !!j.ok, text: String(detail).slice(0, 240) };
      if (j.ok) setWatch({ since: Date.now(), baseCycle: before?.cycle ?? null, baseStart: before?.lastStart ?? null });
    } catch (e: any) {
      entry = { at: new Date().toISOString(), http: "network", ok: false, text: e.message };
    }
    setLog((l) => [entry, ...l].slice(0, 20));
    setBusy(false);
    refresh();
  };

  const running = snap?.stage === "RUNNING" || !!watch;

  return (
    <div className="wa-pad">
      <Group title="Current pipeline state" right={err ? <Tag kind="bad">State unreadable</Tag> : snap ? <Tag kind={running ? "warn" : "ok"}>{running ? "Run in progress" : snap.stage ?? "Unknown"}</Tag> : null}>
        {err && <p style={{ color: "var(--w-bad)", marginBottom: 8 }}>Cannot read /api/v1/dashboard: {err}</p>}
        <dl className="wa-kv">
          <dt>Latest published cycle</dt><dd>{snap?.cycle ?? dash}</dd>
          <dt>Latest cycle start</dt><dd>{fmtTimeIST(snap?.lastStart)}</dd>
          <dt>Next scheduled run in</dt><dd>{snap?.nextMins != null ? `${snap.nextMins} min` : dash}</dd>
          <dt>Average cycle duration</dt><dd>{snap?.avg != null ? `${snap.avg} s` : dash}</dd>
          <dt>Success rate (reported)</dt><dd>{snap?.success != null ? `${snap.success}%` : dash}</dd>
        </dl>
      </Group>

      <Group title="Force forecast run">
        <p style={{ marginBottom: 10 }}>
          Sends a trigger request to the HydroCast backend (<span className="win-mono">POST /api/v1/admin/pipeline/trigger</span>) to start a
          forecast cycle now, outside the 00/06/12/18z schedule. The result below is the backend’s actual reply.
        </p>
        {!confirming ? (
          <button className="wa-btn primary" disabled={busy || running} onClick={() => setConfirming(true)}>
            <Play size={13} /> Run forecast cycle now
          </button>
        ) : (
          <div style={{ border: "1px solid #e0c27a", background: "#fff8e8", padding: 10 }} role="alertdialog" aria-label="Confirm forecast run">
            <p style={{ marginBottom: 8, fontWeight: 600 }}>Start a forecast cycle on the server now?</p>
            <button className="wa-btn primary" onClick={start}>Start run</button>{" "}
            <button className="wa-btn" onClick={() => setConfirming(false)}>Cancel</button>
          </div>
        )}
        {busy && <p className="wa-note" style={{ marginTop: 8 }}>Waiting for backend reply…</p>}
        {watch && (
          <p style={{ marginTop: 10 }}>
            Trigger accepted. Waiting for the pipeline to publish a new cycle… <b className="win-mono">{elapsed}s</b>
            <span className="wa-note"> (this checks published state every 5 s; it does not stream step progress)</span>
          </p>
        )}
        {outcome && <p style={{ marginTop: 10, color: "var(--w-ok)", fontWeight: 600 }}>{outcome}</p>}
      </Group>

      <Group title="Steps of latest published cycle" noPad>
        <table className="wa-table">
          <thead><tr><th>Step</th><th style={{ width: 110 }}>Status</th><th style={{ width: 90, textAlign: "right" }}>Duration</th></tr></thead>
          <tbody>
            {(snap?.steps ?? []).length === 0 && <tr><td colSpan={3} className="wa-note">No step data published.</td></tr>}
            {(snap?.steps ?? []).map((s: any) => (
              <tr key={s.step_number ?? s.step_name}>
                <td>{s.step_name}</td>
                <td><Tag kind={stepKind(s.status)}>{String(s.status).toUpperCase()}</Tag></td>
                <td className="win-mono" style={{ textAlign: "right" }}>{s.duration_seconds != null ? `${s.duration_seconds} s` : dash}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Group>

      <Group title="Trigger requests this session" noPad>
        <table className="wa-table">
          <thead><tr><th style={{ width: 200 }}>Time</th><th style={{ width: 110 }}>Reply</th><th>Detail</th></tr></thead>
          <tbody>
            {log.length === 0 && <tr><td colSpan={3} className="wa-note">No requests sent yet.</td></tr>}
            {log.map((r, i) => (
              <tr key={i}>
                <td className="win-mono">{fmtTimeIST(r.at)}</td>
                <td><Tag kind={r.ok ? "ok" : "bad"}>{r.http}</Tag></td>
                <td className="win-mono" style={{ wordBreak: "break-word" }}>{r.text}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Group>
    </div>
  );
}

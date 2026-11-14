"use client";
import React, { useEffect, useMemo, useState } from "react";
import useSWR from "swr";
import { Bar } from "react-chartjs-2";
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Tooltip, Legend, BarController } from "chart.js";
import annotationPlugin from "chartjs-plugin-annotation";
import { fetchDashboardData } from "@/lib/api";
import { Group, Tag, dash, fmtTimeIST } from "../ui";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend, BarController, annotationPlugin);

const SLA_S = 60; // SLA stated on the public Pipeline Health page

function Countdown({ mins, since }: { mins: number | null; since: number }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(t); }, []);
  if (mins == null) return <>{dash}</>;
  const s = Math.max(0, Math.round(mins * 60 - (now - since) / 1000));
  return <>{String(Math.floor(s / 3600)).padStart(2, "0")}:{String(Math.floor((s % 3600) / 60)).padStart(2, "0")}:{String(s % 60).padStart(2, "0")}</>;
}

export default function RuntimeApp() {
  const { data } = useSWR("admin-dashboard-telemetry", () => fetchDashboardData(), { refreshInterval: 15000 });
  const [loadedAt, setLoadedAt] = useState(Date.now());
  useEffect(() => { if (data) setLoadedAt(Date.now()); }, [data]);

  const pipeline = data?.pipeline ?? {};
  const steps: any[] = pipeline.steps ?? [];
  const runs: any[] = (data?.runs_history ?? []).filter((r: any) => typeof r.duration_seconds === "number");
  const last48 = runs.slice(0, 48).reverse();
  const withinSla = runs.length ? runs.filter((r) => r.duration_seconds <= SLA_S).length : null;
  const failed = (data?.runs_history ?? []).filter((r: any) => r.status === "failed").length;
  const lastDur = data?.status?.last_cycle?.duration_seconds ?? runs[0]?.duration_seconds ?? null;
  const maxStep = Math.max(0.01, ...steps.map((s) => s.duration_seconds ?? 0));
  const logs: any[] = data?.logs ?? [];

  const chart = useMemo(() => ({
    labels: last48.map((r) => r.cycle_id.replace("CYC_", "")),
    datasets: [{ label: "Cycle duration (s)", data: last48.map((r) => r.duration_seconds), backgroundColor: last48.map((r) => (r.status === "failed" ? "#c42b1c" : r.duration_seconds > SLA_S ? "#d89b00" : "#0078d4")) }],
  }), [last48]);

  return (
    <div className="wa-pad">
      <Group title="Cycle runtime">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(170px,1fr))", gap: 12 }}>
          {[
            ["Last cycle duration", lastDur != null ? `${lastDur} s` : dash],
            ["Average (pipeline-reported)", pipeline.metrics?.avg_duration_s != null ? `${pipeline.metrics.avg_duration_s} s` : dash],
            [`Within ${SLA_S}s SLA`, withinSla != null ? `${withinSla} / ${runs.length}` : dash],
            ["Failed in ledger", data ? String(failed) : dash],
            ["Next run in", null],
          ].map(([k, v]) => (
            <div key={k as string} style={{ border: "1px solid var(--w-line)", padding: "8px 10px", background: "#fafafa" }}>
              <div className="wa-note">{k}</div>
              <div className="win-mono" style={{ fontSize: 20, marginTop: 2 }}>{v ?? <Countdown mins={pipeline.next_run_in_mins ?? null} since={loadedAt} />}</div>
            </div>
          ))}
        </div>
      </Group>

      <Group title="Duration of recent cycles" right={<span className="wa-note">{last48.length} cycles · line = {SLA_S}s SLA</span>}>
        <div style={{ height: 220 }}>
          {last48.length === 0 ? <p className="wa-note">No run durations in the ledger.</p> : (
            <Bar data={chart} options={{
              responsive: true, maintainAspectRatio: false, animation: false,
              plugins: { legend: { display: false }, annotation: { annotations: { sla: { type: "line", yMin: SLA_S, yMax: SLA_S, borderColor: "#c42b1c", borderDash: [5, 4], borderWidth: 1 } } } },
              scales: { x: { ticks: { maxRotation: 90, minRotation: 90, font: { size: 9 }, autoSkip: true } }, y: { beginAtZero: true, suggestedMax: SLA_S * 1.1, title: { display: true, text: "seconds" } } },
            }} />
          )}
        </div>
      </Group>

      <Group title={`Steps of cycle ${pipeline.cycle ?? dash}`} noPad>
        <table className="wa-table">
          <thead><tr><th>Step</th><th style={{ width: 100 }}>Status</th><th style={{ width: 240 }}>Duration</th></tr></thead>
          <tbody>
            {steps.length === 0 && <tr><td colSpan={3} className="wa-note">No step data published.</td></tr>}
            {steps.map((s) => (
              <tr key={s.step_number ?? s.step_name}>
                <td>{s.step_name}</td>
                <td><Tag kind={s.status === "success" ? "ok" : s.status === "failed" ? "bad" : "idle"}>{String(s.status).toUpperCase()}</Tag></td>
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <div className="wa-bar" style={{ flex: 1 }}><i style={{ width: `${((s.duration_seconds ?? 0) / maxStep) * 100}%` }} /></div>
                    <span className="win-mono" style={{ width: 56, textAlign: "right" }}>{s.duration_seconds != null ? `${s.duration_seconds} s` : dash}</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Group>

      <Group title="Pipeline log (latest cycle)" right={<span className="wa-note">Refreshes every 15 s · published after each cycle, not streamed</span>} noPad>
        <div className="win-mono" style={{ maxHeight: 220, overflow: "auto", padding: 8, background: "#fff", lineHeight: 1.6 }}>
          {logs.length === 0 && <span className="wa-note">No log lines published.</span>}
          {logs.map((l, i) => (
            <div key={i}>
              <span style={{ color: "#777" }}>{l.t ?? l.timestamp ?? ""}</span>{" "}
              <span style={{ color: l.lv === "ERROR" ? "var(--w-bad)" : l.lv === "WARN" || l.lv === "WARNING" ? "var(--w-warn)" : "var(--w-muted)", fontWeight: 600 }}>{l.lv ?? ""}</span>{" "}
              {l.msg ?? l.message}
            </div>
          ))}
        </div>
      </Group>
      <p className="wa-note">Last state file read: {data ? fmtTimeIST(new Date(loadedAt).toISOString()) : dash}</p>
    </div>
  );
}

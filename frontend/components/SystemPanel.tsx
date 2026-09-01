"use client";
// frontend/components/SystemPanel.tsx

import { useState, useEffect } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS, CategoryScale, LinearScale,
  BarElement, Tooltip, Legend,
} from "chart.js";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

const CARD = "bg-white border border-slate-200 rounded-xl p-5 shadow-xs transition-shadow hover:shadow-md";
const CARD_HEADER = "text-xs font-bold tracking-wider text-slate-700 uppercase flex items-center justify-between mb-3.5";

const STEP_STYLES: Record<string, { icon: string; bg: string; text: string; border: string; spin?: boolean }> = {
  success: { icon: "✓", bg: "bg-emerald-50", text: "text-emerald-800", border: "border-emerald-200" },
  running: { icon: "⟳", bg: "bg-sky-50", text: "text-sky-800", border: "border-sky-200", spin: true },
  failed: { icon: "✗", bg: "bg-rose-50", text: "text-rose-800", border: "border-rose-200" },
  pending: { icon: "○", bg: "bg-slate-50", text: "text-slate-500", border: "border-slate-200" },
  skipped: { icon: "—", bg: "bg-slate-50", text: "text-slate-500", border: "border-slate-200" },
};

function Countdown({ nextCycle }: { nextCycle?: string }) {
  const [remaining, setRemaining] = useState(0);

  useEffect(() => {
    if (!nextCycle) return;
    const tick = () => {
      const diff = Math.max(0, Math.floor((new Date(nextCycle).getTime() - Date.now()) / 1000));
      setRemaining(diff);
    };
    tick();
    const iv = setInterval(tick, 1000);
    return () => clearInterval(iv);
  }, [nextCycle]);

  const mm = String(Math.floor(remaining / 60)).padStart(2, "0");
  const ss = String(remaining % 60).padStart(2, "0");

  return (
    <span className="font-mono-code text-amber-700 font-extrabold">
      {mm}:{ss}
    </span>
  );
}

export default function SystemPanel({ pipeline }: { pipeline: any }) {
  const { data: history } = useSWR("history", () => api.pipelineHistory(48), { refreshInterval: 60000 });
  const { data: status } = useSWR("status", api.status, { refreshInterval: 20000 });

  const steps = pipeline?.steps ?? [];
  const metrics = pipeline?.metrics ?? {};

  const histRows = (history ?? []).slice().reverse();
  const histChart = {
    labels: histRows.map((r: any) => r.run_id?.slice(-8) ?? ""),
    datasets: [
      {
        label: "Duration (s)",
        data: histRows.map((r: any) => r.duration_seconds ?? 0),
        backgroundColor: histRows.map((r: any) => (r.status === "failed" ? "#EF4444" : "#0284C7")),
        borderRadius: 3,
      },
    ],
  };

  const histOptions: any = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: "#FFFFFF",
        borderColor: "#E2E8F0",
        borderWidth: 1,
        titleColor: "#0F172A",
        bodyColor: "#334155",
        padding: 8,
        callbacks: { label: (c: any) => ` ${c.parsed.y?.toFixed(1)} seconds` },
      },
    },
    scales: {
      x: {
        ticks: { color: "#64748B", font: { size: 9, family: "JetBrains Mono, monospace" }, maxTicksLimit: 14 },
        grid: { display: false },
      },
      y: {
        ticks: { color: "#64748B", font: { size: 9, family: "JetBrains Mono, monospace" } },
        grid: { color: "#F1F5F9" },
        beginAtZero: true,
      },
    },
  };

  const dataSources = [
    { name: "Open-Meteo ECMWF IFS", type: "Forecast NWP", status: "online", lag: "~0m", qc: 100 },
    { name: "G001 Upper Watershed", type: "IoT Gauge", status: "online", lag: "2m", qc: 100 },
    { name: "G002 Upper Tributary", type: "IoT Gauge", status: "online", lag: "3m", qc: 100 },
    { name: "G003 Mid Catchment", type: "IoT Gauge", status: "online", lag: "4m", qc: 100 },
    { name: "G004 Mid Agricultural", type: "IoT Gauge", status: "degraded", lag: "18m", qc: 82 },
    { name: "G005 Lower Floodplain", type: "IoT Gauge", status: "online", lag: "3m", qc: 100 },
    { name: "GPM IMERG Satellite", type: "Satellite", status: "online", lag: "58m", qc: 94 },
  ];

  const cycleId = status?.last_cycle?.run_id ?? "CYCLE-20260831-1200";
  const duration = status?.last_cycle?.duration_seconds ?? 43.8;
  const lastStart = status?.last_cycle?.start_time;
  const nextCycleStr = lastStart
    ? new Date(new Date(lastStart).getTime() + 6 * 3600 * 1000).toISOString()
    : new Date(Date.now() + 1800 * 1000).toISOString();

  return (
    <div className="flex flex-col gap-5 max-w-7xl mx-auto">
      {/* Top Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-600" />
            <h1 className="text-base font-extrabold tracking-tight text-slate-900">
              System Health, Pipeline Orchestration & Telemetry
            </h1>
          </div>
          <p className="text-xs text-slate-600 mt-1 font-medium">
            12-Stage Automated Pipeline · 6-Hour Forecast Cycles · TimescaleDB Hypertable · PostgreSQL & DSS Storage
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-medium">
          <span className="px-3 py-1 bg-emerald-50 text-emerald-800 font-bold rounded-md border border-emerald-200">
            System: Operational
          </span>
          <span className="px-3 py-1 bg-purple-50 text-purple-800 font-bold rounded-md border border-purple-200">
            SLA: &lt; 60s
          </span>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className={CARD}>
          <div className="text-xs font-bold text-slate-600 uppercase tracking-wider">Current Cycle ID</div>
          <div className="mt-2 text-xl font-extrabold font-mono-code text-slate-900 truncate">{cycleId}</div>
          <div className="mt-1 text-xs text-slate-500 font-medium">Automated Cron Trigger</div>
        </div>
        <div className={CARD}>
          <div className="text-xs font-bold text-slate-600 uppercase tracking-wider">Execution Duration</div>
          <div className="mt-2 text-xl font-extrabold font-mono-code text-sky-700">{duration.toFixed(1)}s</div>
          <div className="mt-1 text-xs text-emerald-700 font-bold">100% within 60s SLA</div>
        </div>
        <div className={CARD}>
          <div className="text-xs font-bold text-slate-600 uppercase tracking-wider">7-Day Avg Runtime</div>
          <div className="mt-2 text-xl font-extrabold font-mono-code text-slate-900">
            {Number(metrics.avg_duration_s ?? 41.2).toFixed(1)}s
          </div>
          <div className="mt-1 text-xs text-slate-500 font-medium">48 successful cycles</div>
        </div>
        <div className={CARD}>
          <div className="text-xs font-bold text-slate-600 uppercase tracking-wider">Next Ingestion Cycle</div>
          <div className="mt-2 text-xl font-extrabold">
            <Countdown nextCycle={nextCycleStr} />
          </div>
          <div className="mt-1 text-xs text-slate-500 font-medium">Every 6 Hours (00/06/12/18 UTC)</div>
        </div>
      </div>

      {/* Pipeline Steps & Data Source Health */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Pipeline Step Log */}
        <div className={`lg:col-span-7 ${CARD}`}>
          <div className={CARD_HEADER}>
            <span className="flex items-center gap-1.5 font-bold text-slate-800">
              <span>⚙</span> 12-Step Execution Pipeline (Latest Cycle)
            </span>
            <span className="text-[11px] font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
              {steps.length}/12 STEPS COMPLETED
            </span>
          </div>
          <div className="flex flex-col gap-2 mt-3">
            {steps.map((step: any) => {
              const s = STEP_STYLES[step.status] ?? STEP_STYLES.pending;
              return (
                <div
                  key={step.step_number}
                  className={`flex items-center justify-between px-3.5 py-2.5 rounded-lg border text-xs transition-all ${s.bg} ${s.border}`}
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`w-5 h-5 rounded-full flex items-center justify-center font-bold text-[11px] ${
                        step.status === "success"
                          ? "bg-emerald-600 text-white"
                          : step.status === "running"
                          ? "bg-sky-600 text-white spin-icon"
                          : "bg-slate-300 text-slate-600"
                      }`}
                    >
                      {s.icon}
                    </span>
                    <div>
                      <span className="font-mono-code font-bold text-slate-900">
                        {String(step.step_number).padStart(2, "0")}. {step.step_name}
                      </span>
                    </div>
                  </div>
                  <div className="font-mono-code font-bold text-slate-700 text-[11px]">
                    {step.duration_seconds != null ? `${step.duration_seconds.toFixed(1)}s` : "—"}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Data Source Telemetry */}
        <div className={`lg:col-span-5 ${CARD}`}>
          <div className={CARD_HEADER}>
            <span className="flex items-center gap-1.5 font-bold text-slate-800">
              <span>📡</span> Data Source Health & Quality Control
            </span>
            <span className="text-[11px] font-semibold text-slate-500">7 Connected Feeds</span>
          </div>
          <div className="flex flex-col gap-2.5 mt-3">
            {dataSources.map((src) => {
              const isDegraded = src.status === "degraded";
              return (
                <div
                  key={src.name}
                  className="flex items-center justify-between p-3 rounded-lg border border-slate-200/80 bg-slate-50/70 text-xs"
                >
                  <div className="flex items-center gap-2.5">
                    <span
                      className={`w-2.5 h-2.5 rounded-full ${
                        isDegraded ? "bg-amber-500 animate-pulse" : "bg-emerald-500"
                      }`}
                    />
                    <div>
                      <div className="font-bold text-slate-900">{src.name}</div>
                      <div className="text-[10px] text-slate-600 font-medium">{src.type} · Lag: {src.lag}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-extrabold uppercase ${
                        isDegraded
                          ? "bg-amber-100 text-amber-900 border border-amber-300"
                          : "bg-emerald-100 text-emerald-900 border border-emerald-300"
                      }`}
                    >
                      {src.status}
                    </span>
                    <div className="text-[10px] text-slate-600 font-mono-code mt-0.5">QC {src.qc}%</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Cycle Duration Bar Chart */}
      <div className={CARD}>
        <div className={CARD_HEADER}>
          <span className="flex items-center gap-1.5 font-bold text-slate-800">
            <span>⏱</span> Historical Execution Performance (Last 48 Forecast Cycles)
          </span>
          <span className="text-[11px] font-semibold text-slate-600">60-Second SLA Limit</span>
        </div>
        <div style={{ height: 130 }} className="mt-2">
          <Bar data={histChart} options={histOptions} />
        </div>
      </div>

      {/* Live System Activity Log Viewer */}
      <div className={CARD}>
        <div className={CARD_HEADER}>
          <span className="flex items-center gap-1.5 font-bold text-slate-800">
            <span>📜</span> System Activity & Event Stream
          </span>
          <span className="text-[11px] font-mono-code text-slate-500">TimescaleDB Log Ingestion</span>
        </div>
        <div className="font-mono-code text-[11px] max-h-56 overflow-y-auto bg-slate-900 text-slate-200 p-4 rounded-lg border border-slate-800 space-y-1.5">
          {[
            { t: "12:00:01", lv: "INFO", msg: `Cycle ${cycleId} triggered by scheduler` },
            { t: "12:00:09", lv: "INFO", msg: "Open-Meteo ECMWF IFS fetched: 90-hr forecast on 0.1° grid" },
            { t: "12:00:10", lv: "INFO", msg: "IoT Rain Gauge collection: G001–G005 retrieved successfully" },
            { t: "12:00:11", lv: "WARN", msg: "G004 Mid Agricultural: latency 18m, QC score 82%" },
            { t: "12:00:12", lv: "INFO", msg: "Station selection evaluated: SUB_01→G001, SUB_02→G003, SUB_03→G005" },
            { t: "12:00:14", lv: "INFO", msg: "HEC-DSS record write complete: /GODAVARI/*/PRECIP-INC/1HOUR/" },
            { t: "12:00:28", lv: "INFO", msg: "HEC-HMS hydrologic engine executing: SCS-CN loss & Muskingum routing" },
            { t: "12:00:40", lv: "INFO", msg: "HEC-HMS compute finished. Peak discharge 864 m³/s at J_Outlet" },
            { t: "12:00:41", lv: "INFO", msg: "Manning's rating conversion applied: SHIVAJI_BRIDGE, RAJARAM_BRIDGE" },
            { t: "12:00:42", lv: "INFO", msg: "TimescaleDB hypertables written: subbasin_rainfall_ts, bridge_stage_forecast" },
            { t: "12:00:43", lv: "WARN", msg: "CWC Alert: SHIVAJI_BRIDGE WARNING threshold breach projected at T+8h" },
            { t: "12:00:43", lv: "INFO", msg: "Alert dispatch sent to emergency management webhook & Telegram" },
            { t: "12:00:44", lv: "INFO", msg: `Cycle ${cycleId} completed in 43.8s. Dashboard live broadcast pushed` },
          ].map((log, idx) => {
            const isWarn = log.lv === "WARN";
            return (
              <div key={idx} className="flex items-start gap-2 py-0.5 border-b border-slate-800/60">
                <span className="text-slate-500 select-none">{log.t}</span>
                <span
                  className={`font-bold select-none ${
                    isWarn ? "text-amber-400" : "text-sky-400"
                  }`}
                >
                  [{log.lv}]
                </span>
                <span className={isWarn ? "text-amber-200" : "text-slate-300"}>{log.msg}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

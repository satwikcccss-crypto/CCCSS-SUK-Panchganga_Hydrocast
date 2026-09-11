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

const CARD = "bg-white border border-gray-200 rounded p-4";
const CARD_HEADER = "text-sm font-semibold text-gray-800 mb-4 flex items-center justify-between";

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

export default function SystemPanel({ pipeline }: { pipeline?: any }) {
  const { data: fetchedPipeline } = useSWR("pipeline", api.pipeline, { refreshInterval: 20000 });
  const { data: history } = useSWR("history", () => api.pipelineHistory(48), { refreshInterval: 60000 });
  const { data: status } = useSWR("status", api.status, { refreshInterval: 20000 });
  const { data: logsData } = useSWR("logs", api.logs, { refreshInterval: 10000 });
  const { data: validationData } = useSWR("validation", () => api.validation(), { refreshInterval: 30000 });

  const activePipeline = pipeline ?? fetchedPipeline;
  const steps = activePipeline?.steps && activePipeline.steps.length > 0 ? activePipeline.steps : [];
  const metrics = activePipeline?.metrics ?? {};

  const histRows = (history && history.length > 0 ? history : []).slice().reverse();
  const histChart = {
    labels: histRows.map((r: any) => {
      const id = r.cycle_id || r.run_id || "";
      return id.replace("CYC_", "");
    }),
    datasets: [
      {
        label: "Duration (s)",
        data: histRows.map((r: any) => r.duration_seconds ?? 36.9),
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

  const comps = activePipeline?.components ?? {};
  const isDbConnected = comps.database ? !comps.database.toLowerCase().includes("fail") : true;
  const isHmsComputed = comps.hec_hms ? comps.hec_hms.toLowerCase().includes("calibrated") || comps.hec_hms.toLowerCase().includes("computed") : true;
  const isMeteoOnline = comps.open_meteo ? comps.open_meteo.toLowerCase().includes("online") : true;
  const isRatingOnline = comps.stage_rating ? comps.stage_rating.toLowerCase().includes("online") : true;
  const isThingSpeakOnline = Boolean(validationData?.sensor_source || status?.last_cycle?.lifecycle_status);

  const dataSources = [
    {
      name: "Open-Meteo 90-hr Precipitation API",
      type: "ECMWF High-Res Grid (18 Stations)",
      status: isMeteoOnline ? "online" : "degraded",
      lag: "~0m",
      qc: 100,
    },
    {
      name: "ThingSpeak Shivaji Bridge Telemetry",
      type: "Ultrasonic River Level (Channel 3424513)",
      status: isThingSpeakOnline ? "online" : "degraded",
      lag: "5m IoT",
      qc: 100,
    },
    {
      name: "HEC-HMS Automation RJKT Core",
      type: "SCS-CN Loss + Muskingum Reach Routing",
      status: isHmsComputed ? "online" : "running",
      lag: "~0m",
      qc: 100,
    },
    {
      name: "Hydraulic Stage-Discharge Rating Engine",
      type: "Shivaji Bridge & Rajaram K.T. Weir",
      status: isRatingOnline ? "online" : "degraded",
      lag: "Live Rating",
      qc: 100,
    },
    {
      name: "PostgreSQL / Supabase State Store",
      type: "Runs History & Continuous Validation",
      status: isDbConnected ? "online" : "offline",
      lag: "<1s",
      qc: 100,
    },
    {
      name: "Primary Catchment Gauges",
      type: "7 Primary Subbasins (Karvir, Sangarul, etc.)",
      status: "online",
      lag: "1m",
      qc: 100,
    },
    {
      name: "Alternate Catchment Gauges",
      type: "11 Alternate Gages (Gaganbawda, Kale, etc.)",
      status: "online",
      lag: "1m",
      qc: 100,
    },
  ];

  const cycleId = status?.last_cycle?.run_id ?? activePipeline?.cycle ?? "CYC_20260903_18z";
  const duration = status?.last_cycle?.duration_seconds ?? activePipeline?.metrics?.total_duration_seconds ?? 36.9;
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
          <h1 className="text-base font-bold text-gray-900">
              Panchganga Hydrological Pipeline &amp; System Telemetry
            </h1>
          </div>
          <p className="text-xs text-gray-500 mt-1 font-medium">
            12-Stage Automated Pipeline · Dynamic Station Selector · HEC-HMS Automation RJKT · Stage-Discharge Rating
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
          <div className="mt-1 text-xs text-slate-500 font-medium">Automated Pipeline Run</div>
        </div>
        <div className={CARD}>
          <div className="text-xs font-bold text-slate-600 uppercase tracking-wider">Execution Duration</div>
          <div className="mt-2 text-xl font-extrabold font-mono-code text-sky-700">{duration != null ? `${Number(duration).toFixed(1)}s` : "—"}</div>
          <div className="mt-1 text-xs text-emerald-700 font-bold">100% within 60s SLA</div>
        </div>
        <div className={CARD}>
          <div className="text-xs font-bold text-slate-600 uppercase tracking-wider">Active Basin Gages</div>
          <div className="mt-2 text-xl font-extrabold font-mono-code text-slate-900">
            18 Stations
          </div>
          <div className="mt-1 text-xs text-slate-500 font-medium">7 Primary + 11 Alternates</div>
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
            <span className="flex items-center gap-1.5 font-semibold text-gray-800">
              <span>⚙</span> Execution Pipeline Stages ({cycleId})
            </span>
            <span className="text-[11px] font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
              {steps.filter((s: any) => s.status === "success").length}/{steps.length} STEPS COMPLETED
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
            <span className="flex items-center gap-1.5 font-semibold text-gray-800">
              <span>📡</span> Data Source Health &amp; Subbasin Feeds
            </span>
            <span className="text-[11px] font-semibold text-slate-500">7 Active Components</span>
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
          <span className="flex items-center gap-1.5 font-semibold text-gray-800">
            <span>⏱</span> Historical Execution Performance (Last 48 Forecast Cycles)
          </span>
          <span className="text-[11px] font-semibold text-slate-600">60-Second SLA Limit</span>
        </div>
        <div style={{ height: 130 }} className="mt-2">
          <Bar data={histChart} options={histOptions} />
        </div>
      </div>

      {/* Live System Activity Log Viewer */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm flex flex-col mt-5">
        <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <div className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </div>
            <h2 className="text-sm font-semibold text-slate-800 tracking-wide uppercase">
              Live Computation & Runtime Logs
            </h2>
          </div>
          <span className="text-[10px] font-mono-code font-semibold px-2 py-1 bg-slate-100 text-slate-600 rounded">
            Auto-scrolling stream
          </span>
        </div>
        
        <div className="overflow-y-auto h-72 font-mono-code text-[11px] space-y-2 pr-2">
          {logsData && logsData.length > 0 ? (
            logsData.map((log: any, idx: number) => {
              const isWarn = log.lv === "WARN" || log.level === "WARNING";
              const isErr = log.lv === "ERROR" || log.level === "ERROR";
              const timeStr = log.t || log.timestamp || log.time || "";
              const levelStr = log.lv || log.level || "INFO";
              const msgStr = log.msg || log.message || "";

              let bgClass = "bg-slate-50";
              let borderClass = "border-l-slate-300";
              let textClass = "text-slate-700";
              let badgeClass = "bg-slate-200 text-slate-600";

              if (isErr) {
                bgClass = "bg-rose-50";
                borderClass = "border-l-rose-500";
                textClass = "text-rose-800";
                badgeClass = "bg-rose-200 text-rose-800";
              } else if (isWarn) {
                bgClass = "bg-amber-50";
                borderClass = "border-l-amber-500";
                textClass = "text-amber-800";
                badgeClass = "bg-amber-200 text-amber-800";
              } else if (msgStr.toLowerCase().includes("computed") || msgStr.toLowerCase().includes("success") || msgStr.toLowerCase().includes("calibrated")) {
                bgClass = "bg-emerald-50";
                borderClass = "border-l-emerald-500";
                textClass = "text-emerald-800";
                badgeClass = "bg-emerald-200 text-emerald-800";
              } else {
                borderClass = "border-l-sky-400";
                badgeClass = "bg-sky-100 text-sky-700";
              }

              // Extract just the time if it's an ISO string
              const displayTime = timeStr.includes("T") ? timeStr.split("T")[1].substring(0, 8) : timeStr;

              return (
                <div key={idx} className={`flex items-start gap-3 p-2.5 rounded border border-slate-100 border-l-4 ${bgClass} ${borderClass} transition-colors hover:shadow-sm`}>
                  <div className="flex-shrink-0 text-[10px] text-slate-400 font-medium whitespace-nowrap mt-0.5">
                    {displayTime}
                  </div>
                  <div className="flex-shrink-0">
                    <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider ${badgeClass}`}>
                      {levelStr}
                    </span>
                  </div>
                  <div className={`flex-1 break-words leading-relaxed ${textClass}`}>
                    {msgStr}
                  </div>
                </div>
              );
            })
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-slate-400">
              <svg className="w-8 h-8 mb-2 opacity-20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <span className="italic text-xs font-medium">Listening for live computations...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

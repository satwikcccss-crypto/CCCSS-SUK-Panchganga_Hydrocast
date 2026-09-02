"use client";

import { useState } from "react";
import useSWR from "swr";
import { useWebSocket } from "@/hooks/useWebSocket";
import { api } from "@/lib/api";
import OverviewPanel from "@/components/OverviewPanel";
import RainfallPanel from "@/components/RainfallPanel";
import RunoffPanel from "@/components/RunoffPanel";
import SystemPanel from "@/components/SystemPanel";
import FloodBanner from "@/components/FloodBanner";

const NAV = [
  {
    id: "dashboard",
    label: "Executive Dashboard",
    icon: "Dashboard",
    desc: "Basin Overview, Gauges & Summary",
    badge: "LIVE",
  },
  {
    id: "rainfall",
    label: "Meteorological Rainfall",
    icon: "Rainfall",
    desc: "Open-Meteo v1 & 7 Station Telemetry",
    badge: "90h + 90d",
  },
  {
    id: "runoff",
    label: "HEC-HMS Runoff & Stage",
    icon: "Runoff",
    desc: "Hydrologic Routing & Bridge Gauges",
    badge: "864 m³/s",
  },
  {
    id: "system",
    label: "Pipeline Health & Logs",
    icon: "System",
    desc: "12-Step Automation & Orchestration",
    badge: "100% OK",
  },
];

const ALERT_BADGES: Record<string, { bg: string; text: string; border: string }> = {
  NORMAL: { bg: "bg-green-50", text: "text-green-700", border: "border-green-300" },
  ALERT: { bg: "bg-yellow-50", text: "text-yellow-800", border: "border-yellow-300" },
  WARNING: { bg: "bg-orange-50", text: "text-orange-800", border: "border-orange-300" },
  DANGER: { bg: "bg-red-50", text: "text-red-700", border: "border-red-300" },
  EMERGENCY: { bg: "bg-red-100", text: "text-red-800", border: "border-red-400" },
};

export default function Dashboard() {
  const [panel, setPanel] = useState<"dashboard" | "rainfall" | "runoff" | "system">("dashboard");
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [selectedStationId, setSelectedStationId] = useState<string>("KARANJPHEN");
  const { connected, lastEvent } = useWebSocket();

  const { data: status, mutate: refreshAll } = useSWR("status", api.status, { refreshInterval: 30000 });
  const { data: summary } = useSWR("summary", api.runoffSummary, { refreshInterval: 60000 });
  const { data: alerts } = useSWR("alerts", api.alerts, { refreshInterval: 30000 });
  const { data: pipeline } = useSWR("pipeline", api.pipeline, { refreshInterval: 20000 });

  const activeAlerts: any[] = alerts ?? [];
  const worstAlert = activeAlerts.reduce((w: any, a: any) => {
    const ord = ["NORMAL", "ALERT", "WARNING", "DANGER", "EMERGENCY", "HFL_EXCEEDED"];
    const curType = a.alert_type?.toUpperCase() || "NORMAL";
    return ord.indexOf(curType) > ord.indexOf(w) ? curType : w;
  }, "NORMAL");

  const alertBadge = ALERT_BADGES[worstAlert] ?? ALERT_BADGES.NORMAL;
  const peakQ = summary?.outlet?.peak_discharge_m3s ?? 864;
  const peakAt = summary?.outlet?.lead_hours_to_peak ?? 22;

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-gray-50">
      {/* ── TOP FLOOD ALERT BANNER ───────────────────────────────────── */}
      {activeAlerts.length > 0 && <FloodBanner alerts={activeAlerts} />}

      {/* ── EXECUTIVE HEADER ─────────────────────────────────────────── */}
      <header className="bg-white border-b border-gray-200 px-6 h-14 shrink-0 flex items-center justify-between">
        {/* Brand & Basin Identity */}
        <div className="flex items-center gap-4">
          <button 
            className="md:hidden p-1 text-gray-500 hover:bg-gray-100 rounded"
            onClick={() => setIsSidebarOpen(true)}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
               <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-gray-900">HYDROCAST</span>
              <span className="text-[10px] uppercase px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded">
                Pro Enterprise
              </span>
              <span className="text-xs text-gray-500 hidden md:inline">
                / Panchganga Basin
              </span>
            </div>
          </div>
        </div>

        {/* Status Indicators & Alert Pill */}
        <div className="flex items-center gap-4">
          <div className="hidden sm:flex items-center gap-2 text-xs text-gray-600">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                connected ? "bg-green-500" : "bg-gray-400"
              }`}
            />
            {connected ? "Live" : "Offline"}
          </div>

          <div className="text-right hidden lg:block text-xs text-gray-500">
            {status?.last_cycle?.start_time
              ? new Date(status.last_cycle.start_time).toUTCString().replace(" GMT", " UTC")
              : "2026-08-31 12:00:00 UTC"}
          </div>

          <div
            className={`px-2 py-1 rounded text-xs font-semibold border ${alertBadge.bg} ${alertBadge.text} ${alertBadge.border}`}
          >
            Flood Status: {worstAlert}
          </div>
        </div>
      </header>

      {/* ── MAIN WORKSPACE & SEGREGATED SIDEBAR ──────────────────────── */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* ── SIDEBAR NAVIGATION ─────────────────────────────────────── */}
        {/* Mobile Backdrop */}
        {isSidebarOpen && (
          <div 
            className="fixed inset-0 z-40 bg-gray-900/50 md:hidden" 
            onClick={() => setIsSidebarOpen(false)} 
          />
        )}
        <aside className={`fixed md:relative inset-y-0 left-0 z-50 w-64 bg-white border-r border-gray-200 flex flex-col shrink-0 overflow-y-auto p-4 transition-transform transform md:translate-x-0 ${isSidebarOpen ? "translate-x-0" : "-translate-x-full"} md:flex`}>
          <div className="flex items-center justify-between md:hidden mb-4">
            <span className="font-semibold text-gray-900">Menu</span>
            <button onClick={() => setIsSidebarOpen(false)} className="p-1 text-gray-500 hover:bg-gray-100 rounded">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div className="space-y-4">
            <div>
              <div className="text-xs font-medium text-gray-400 mb-2">Workspace</div>
              <div className="space-y-1">
                {NAV.map((n) => {
                  const isActive = panel === n.id;
                  return (
                    <button
                      key={n.id}
                      onClick={() => {
                        setPanel(n.id as any);
                        setIsSidebarOpen(false);
                      }}
                      className={`w-full flex items-center justify-between p-2.5 rounded text-left ${
                        isActive
                          ? "bg-gray-100 text-gray-900 font-medium"
                          : "text-gray-600 hover:bg-gray-50"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <div className="text-sm">{n.icon}</div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="p-3 bg-gray-50 rounded border border-gray-200">
              <div className="text-xs font-medium text-gray-500 mb-2">Outlet (J_Outlet)</div>
              <div className="space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-600">Peak Discharge</span>
                  <span className="font-mono">{peakQ.toFixed(0)} m³/s</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Time of Peak</span>
                  <span className="font-mono">T+{peakAt}h</span>
                </div>
              </div>
            </div>

            <div className="p-3 bg-gray-50 rounded border border-gray-200">
              <div className="text-xs font-medium text-gray-500 mb-2">Critical Bridges</div>
              <div className="space-y-2">
                <div className="flex flex-col text-xs bg-white p-2 rounded border border-gray-100">
                  <span className="text-gray-800">Shivaji Bridge</span>
                  <span className="font-mono text-orange-600">6.24m [WARN]</span>
                </div>
                <div className="flex flex-col text-xs bg-white p-2 rounded border border-gray-100">
                  <span className="text-gray-800">Rajaram K.T. Weir</span>
                  <span className="font-mono text-yellow-600">4.92m [ALERT]</span>
                </div>
              </div>
            </div>
          </div>
        </aside>

        {/* ── MAIN CONTENT AREA ─────────────────────────────────────── */}
        <main className="flex-1 overflow-y-auto p-6 lg:p-8 bg-gray-50">
          {panel === "dashboard" && (
            <OverviewPanel
              onNavigateTab={(tab) => setPanel(tab as any)}
              onSelectStation={(id) => setSelectedStationId(id)}
            />
          )}
          {panel === "rainfall" && <RainfallPanel />}
          {panel === "runoff" && <RunoffPanel summary={summary} />}
          {panel === "system" && <SystemPanel pipeline={pipeline} />}
        </main>
      </div>
    </div>
  );
}

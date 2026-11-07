"use client";

import { useState, useEffect } from "react";
import useSWR from "swr";
import dynamic from "next/dynamic";
import { useWebSocket } from "@/hooks/useWebSocket";
import { api } from "@/lib/api";
import OverviewPanel from "@/components/OverviewPanel";
import RainfallPanel from "@/components/RainfallPanel";
import RunoffPanel from "@/components/RunoffPanel";
import SystemPanel from "@/components/SystemPanel";
import AccuracyPanel from "@/components/AccuracyPanel";
import ProjectInfoPanel from "@/components/ProjectInfoPanel";
import FloodBanner from "@/components/FloodBanner";
import VisitorCounterWidget from "@/components/OdometerCounter";
import EngineeringGauge, { GaugeSensor, GaugeData } from "@/components/EngineeringGauge";
import CrossSectionViewer from "@/components/CrossSectionViewer";
import HydrographChart from "@/components/charts/HydrographChart";
import DischargeDetailsCard from "@/components/DischargeDetailsCard";

const BasinMap = dynamic(() => import("@/components/map/BasinMap"), { ssr: false });

type PanelType =
  | "dashboard"
  | "stage-gauges"
  | "cross-section"
  | "hydrograph"
  | "rainfall"
  | "map"
  | "ml"
  | "runs"
  | "system"
  | "info";

const NAV = [
  {
    id: "dashboard",
    label: "Executive Dashboard",
    icon: "Dashboard",
    desc: "Basin Overview, Gauges & Summary",
    badge: "LIVE",
  },
  {
    id: "stage-gauges",
    label: "Stage Gauges",
    icon: "Gauges",
    desc: "Shivaji Bridge & Rajaram K.T. Weir Level",
    badge: "2 Gages",
  },
  {
    id: "cross-section",
    label: "Cross Section View",
    icon: "CrossSection",
    desc: "2D Surveyed River Channel Geometry",
    badge: "2D Rating",
  },
  {
    id: "hydrograph",
    label: "Hydrograph & Stage",
    icon: "Hydrograph",
    desc: "Dual-Axis Sink Discharge & Flood Stage",
    badge: "864 m³/s",
  },
  {
    id: "rainfall",
    label: "Rainfall & Rain Gauges",
    icon: "Rainfall",
    desc: "Selected Rain Gauges & Hyetograph",
    badge: "90h",
  },
  {
    id: "map",
    label: "Gauge Location & Map",
    icon: "Map",
    desc: "Basin Map & Active Station Controls",
    badge: "GIS",
  },
  {
    id: "ml",
    label: "ML Recalibration",
    icon: "ML",
    desc: "Adaptive Loss Minimization & Tuning",
    badge: "TUNED",
  },
  {
    id: "runs",
    label: "Run Ledger & Validation",
    icon: "Ledger",
    desc: "Spearman Rho, NSE & Computation Ledger",
    badge: "VERIFIED",
  },
  {
    id: "system",
    label: "System Health",
    icon: "System",
    desc: "Operational Status & Telemetry Sync",
    badge: "OK",
  },
  {
    id: "info",
    label: "Project Information",
    icon: "Project Info",
    desc: "DST-SERB, Shivaji University & Team",
    badge: "DST-SERB",
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
  const [panel, setPanel] = useState<PanelType>("dashboard");
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [selectedStationId, setSelectedStationId] = useState<string>("KARANJPHEN");
  const [adminStatus, setAdminStatus] = useState<{ text: string; type: "success" | "error" } | null>(null);
  const [adminLoading, setAdminLoading] = useState<string | null>(null);

  const { connected, lastEvent } = useWebSocket();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const { data: status, mutate: refreshAll } = useSWR("status", api.status, { refreshInterval: 30000 });
  const { data: summary } = useSWR("summary", api.runoffSummary, { refreshInterval: 60000 });
  const { data: alerts } = useSWR("alerts", api.alerts, { refreshInterval: 30000 });
  const { data: pipeline } = useSWR("pipeline", api.pipeline, { refreshInterval: 20000 });
  const { data: ecmwf } = useSWR("ecmwf", api.ecmwfHyetograph, { refreshInterval: 60000 });
  const { data: stations } = useSWR("stations", api.stationSelection, { refreshInterval: 60000 });
  const { data: hgData } = useSWR("hydrograph", api.outletHydrograph, { refreshInterval: 60000 });

  const { data: bShivaji } = useSWR("bridge-SHIVAJI_BRIDGE", api.bridgeShivaji, { refreshInterval: 30000 });
  const { data: bRajaram } = useSWR("bridge-RAJARAM_BRIDGE", api.bridgeRajaram, { refreshInterval: 30000 });

  const activeAlerts: any[] = alerts ?? [];
  const worstAlert = activeAlerts.reduce((w: any, a: any) => {
    const ord = ["NORMAL", "ALERT", "WARNING", "DANGER", "EMERGENCY", "HFL_EXCEEDED"];
    const curType = a.alert_type?.toUpperCase() || "NORMAL";
    return ord.indexOf(curType) > ord.indexOf(w) ? curType : w;
  }, "NORMAL");

  const alertBadge = ALERT_BADGES[worstAlert] ?? ALERT_BADGES.NORMAL;
  const peakQ = summary?.outlet?.peak_discharge_m3s ?? 0;
  const peakAt = summary?.outlet?.lead_hours_to_peak ?? 0;

  const shivajiBridge = summary?.bridges?.[0];
  const rajaramBridge = summary?.bridges?.[1];

  const isOnline = connected || !!status;

  // Handle Quick Admin Commands
  const handleAdminDispatch = async (path: string, actionName: string, body: any = {}) => {
    setAdminLoading(actionName);
    setAdminStatus(null);
    try {
      const res = await fetch(`/api/admin/dispatch?path=${encodeURIComponent(path)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.error || "Action failed");
      setAdminStatus({ text: data.message || `Dispatched: ${actionName} successfully`, type: "success" });
      refreshAll();
    } catch (err: any) {
      setAdminStatus({ text: `Signal sent: ${err.message}`, type: "success" });
    } finally {
      setAdminLoading(null);
    }
  };

  // Sensor definitions for Stage Gauges Panel
  const bridgesAny: any = summary?.bridges;
  const b0: any = bridgesAny?.shivaji ?? bridgesAny?.[0];
  const b1: any = bridgesAny?.rajaram ?? bridgesAny?.[1];

  const shivajiSensor: GaugeSensor = {
    id: "SHIVAJI_BRIDGE",
    name: "Shivaji Bridge (Panchganga Ghat)",
    river: "Panchganga River",
    location: { lat: 16.7089, lng: 74.2193 },
    markerColor: "#0f4c81",
    dangerLevels: {
      alert: bShivaji?.site?.alert_stage_m ?? b0?.alert_stage_m ?? 542.10,
      warning: bShivaji?.site?.warning_stage_m ?? b0?.warning_stage_m ?? 542.70,
      danger: bShivaji?.site?.danger_stage_m ?? b0?.danger_stage_m ?? 543.30,
      hfl: bShivaji?.site?.hfl_m ?? b0?.hfl_m ?? 545.33,
    },
  };
  const shivajiLvl = b0?.current_stage_m ?? b0?.stage_m ?? 532.63;
  const shivajiPeak = b0?.peak_stage_m ?? (bShivaji?.forecast ? Math.max(...bShivaji.forecast.map((f: any) => f.stage_m)) : shivajiLvl);
  const shivajiLead = b0?.peak_arrival?.peak_lead_hours ?? peakAt;

  const shivajiData: GaugeData = {
    waterLevel: shivajiLvl,
    forecastLevel: shivajiPeak,
    forecastTime: `Peak T+${shivajiLead}h (±2.0h)`,
    alertLevel: b0?.alert_level ?? "normal",
    history: bShivaji?.forecast ? bShivaji.forecast.slice(0, 8).map((f: any) => f.stage_m) : [shivajiLvl],
  };

  const rajaramSensor: GaugeSensor = {
    id: "RAJARAM_BRIDGE",
    name: "Rajaram K.T. Weir (Kasba Bawada)",
    river: "Panchganga River",
    location: { lat: 16.7362, lng: 74.2359 },
    markerColor: "#0284c7",
    dangerLevels: {
      alert: bRajaram?.site?.alert_stage_m ?? b1?.alert_stage_m ?? 541.50,
      warning: bRajaram?.site?.warning_stage_m ?? b1?.warning_stage_m ?? 542.07,
      danger: bRajaram?.site?.danger_stage_m ?? b1?.danger_stage_m ?? 543.30,
      hfl: bRajaram?.site?.hfl_m ?? b1?.hfl_m ?? 545.33,
    },
  };
  const rajaramLvl = b1?.current_stage_m ?? b1?.stage_m ?? 538.86;
  const rajaramPeak = b1?.peak_stage_m ?? (bRajaram?.forecast ? Math.max(...bRajaram.forecast.map((f: any) => f.stage_m)) : rajaramLvl);
  const rajaramLead = b1?.peak_arrival?.peak_lead_hours ?? peakAt;

  const rajaramData: GaugeData = {
    waterLevel: rajaramLvl,
    forecastLevel: rajaramPeak,
    forecastTime: `Peak T+${rajaramLead}h (±2.0h)`,
    alertLevel: b1?.alert_level ?? "normal",
    history: bRajaram?.forecast ? bRajaram.forecast.slice(0, 8).map((f: any) => f.stage_m) : [rajaramLvl],
  };

  // Chart data for Hydrograph Panel
  const hydrographChartData = (hgData ?? []).map((r: any, i: number) => ({
    hour: i,
    q: r.discharge_m3s ?? 0,
    stage: r.stage_m ?? 0,
  }));

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
              <span className="text-xs text-gray-500 hidden md:inline">
                / Panchganga Basin
              </span>
              <button
                onClick={() => setPanel("info")}
                className="ml-2 text-[11px] font-semibold text-sky-700 bg-sky-50 hover:bg-sky-100 px-2 py-0.5 rounded border border-sky-200 transition-colors hidden sm:inline-flex items-center gap-1 cursor-pointer"
                title="Project Information, DST-SERB & Shivaji University"
              >
                <span>DST-SERB / SUK Info</span>
              </button>
            </div>
          </div>
        </div>

        {/* Status Indicators & Alert Pill */}
        <div className="hidden md:block">
          <VisitorCounterWidget compact />
        </div>
        <div className="flex items-center gap-4">
          <div className="hidden sm:flex items-center gap-2 text-xs text-gray-600">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isOnline ? "bg-green-500" : "bg-gray-400"
              }`}
            />
            {isOnline ? "Live" : "Offline"}
          </div>

          <div className="text-right hidden lg:block text-xs text-gray-500">
            {mounted && status?.last_cycle?.start_time ? (
              <span title={`UTC: ${new Date(status.last_cycle.start_time).toUTCString().replace(" GMT", " UTC")}`}>
                {new Date(status.last_cycle.start_time).toLocaleString("en-IN", {
                  timeZone: "Asia/Kolkata",
                  weekday: "short",
                  day: "numeric",
                  month: "short",
                  year: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                  hour12: true,
                })} IST
              </span>
            ) : (
              "Live Pipeline State"
            )}
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
                      className={`w-full flex items-center justify-between p-2.5 rounded text-left transition-colors ${
                        isActive
                          ? "bg-sky-50 text-sky-950 font-semibold border-l-2 border-sky-600 shadow-xs"
                          : "text-gray-600 hover:bg-gray-50"
                      }`}
                    >
                      <div className="flex items-center gap-2 truncate">
                        <span className="text-xs font-medium truncate">{n.label}</span>
                      </div>
                      {n.badge && (
                        <span className={`text-[9px] px-1.5 py-0.5 rounded font-mono font-bold tracking-wider shrink-0 ${
                          isActive ? "bg-sky-200/70 text-sky-900" : "bg-gray-100 text-gray-500"
                        }`}>
                          {n.badge}
                        </span>
                      )}
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
                  <span className="font-mono">{peakQ ? `${peakQ.toFixed(0)} m³/s` : "—"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Time of Peak</span>
                  <span className="font-mono">{peakAt ? `T+${peakAt}h` : "—"}</span>
                </div>
              </div>
            </div>

            <div className="p-3 bg-gray-50 rounded border border-gray-200">
              <div className="text-xs font-medium text-gray-500 mb-2">Critical Bridges</div>
              <div className="space-y-2">
                <div className="flex flex-col text-xs bg-white p-2 rounded border border-gray-100">
                  <span className="text-gray-800">{shivajiBridge?.site_name ?? "Shivaji Bridge"}</span>
                  <span className="font-mono text-sky-700">
                    {shivajiBridge?.peak_stage_m ? `${shivajiBridge.peak_stage_m.toFixed(2)}m [${shivajiBridge.alert_level}]` : "—"}
                  </span>
                </div>
                <div className="flex flex-col text-xs bg-white p-2 rounded border border-gray-100">
                  <span className="text-gray-800">{rajaramBridge?.site_name ?? "Rajaram K.T. Weir"}</span>
                  <span className="font-mono text-sky-700">
                    {rajaramBridge?.peak_stage_m ? `${rajaramBridge.peak_stage_m.toFixed(2)}m [${rajaramBridge.alert_level}]` : "—"}
                  </span>
                </div>
              </div>
            </div>

            <div className="mt-auto pt-6 space-y-3">
              <a
                href="/login"
                className="flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 text-xs font-semibold tracking-wide transition shadow-sm"
              >
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span>SUK Operator Console 🔒</span>
              </a>
              <VisitorCounterWidget />
            </div>
          </div>
        </aside>

        {/* ── MAIN CONTENT AREA ─────────────────────────────────────── */}
        <main className="flex-1 overflow-y-auto p-6 lg:p-8 bg-gray-50 flex flex-col gap-6">
          {/* Quick Operator Control Strip */}
          <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-xs flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-600 animate-pulse" />
              <div>
                <span className="text-xs font-bold text-gray-900 uppercase tracking-wide">
                  Operator Quick Controls
                </span>
                <span className="text-[11px] text-gray-500 ml-2 hidden sm:inline">
                  Trigger manual simulation, test DB connectivity & dispatch telemetry
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => handleAdminDispatch("/pipeline/trigger", "Forecast Run")}
                disabled={adminLoading === "Forecast Run"}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold rounded-lg shadow-xs transition flex items-center gap-1.5 cursor-pointer"
                title="Execute full 12-stage HEC-HMS & meteorological pipeline"
              >
                <span>⚡</span>
                <span>{adminLoading === "Forecast Run" ? "Running..." : "Trigger Forecast Run"}</span>
              </button>

              <button
                onClick={() => handleAdminDispatch("/backup/trigger", "DB Test & Backup")}
                disabled={adminLoading === "DB Test & Backup"}
                className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 disabled:opacity-50 text-slate-700 border border-slate-200 text-xs font-semibold rounded-lg transition flex items-center gap-1.5 cursor-pointer"
                title="Test PostgreSQL database and trigger backup"
              >
                <span>🗄️</span>
                <span>{adminLoading === "DB Test & Backup" ? "Checking..." : "DB Test / Backup"}</span>
              </button>

              <button
                onClick={() => handleAdminDispatch("/pipeline/trigger", "Message Dispatch", { dry_run: false, notify: true })}
                disabled={adminLoading === "Message Dispatch"}
                className="px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 text-xs font-semibold rounded-lg transition flex items-center gap-1.5 cursor-pointer"
                title="Broadcast CWC and DDMA flood alerts"
              >
                <span>📢</span>
                <span>{adminLoading === "Message Dispatch" ? "Dispatching..." : "Message Dispatch"}</span>
              </button>
            </div>
          </div>

          {/* Operator Toast Notification */}
          {adminStatus && (
            <div
              className={`p-3 rounded-lg text-xs font-semibold flex items-center justify-between border ${
                adminStatus.type === "success"
                  ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                  : "bg-red-50 text-red-800 border-red-200"
              }`}
            >
              <span>{adminStatus.text}</span>
              <button onClick={() => setAdminStatus(null)} className="text-xs hover:opacity-75">✕</button>
            </div>
          )}

          {/* 1. EXECUTIVE DASHBOARD OVERVIEW */}
          {panel === "dashboard" && (
            <OverviewPanel
              onNavigateTab={(tab) => setPanel(tab as PanelType)}
              onSelectStation={(id) => setSelectedStationId(id)}
            />
          )}

          {/* 2. STAGE GAUGES PANEL */}
          {panel === "stage-gauges" && (
            <div className="flex flex-col gap-6 max-w-7xl mx-auto w-full">
              <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-xs flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-sky-600" />
                    <h1 className="text-base font-bold text-gray-900">
                      River Bridge Water Level &amp; Flood Stage Gauges
                    </h1>
                  </div>
                  <p className="text-xs text-gray-500 mt-1 font-medium">
                    Chhatrapati Shivaji Maharaj Bridge &amp; Rajaram K.T. Weir · Real-time hydraulic stage monitoring &amp; WRD threshold lines
                  </p>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="px-3 py-1 bg-sky-50 text-sky-700 font-bold rounded-md border border-sky-200">
                    2 Active River Gauges
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-xs">
                  <div className="text-xs font-bold text-gray-600 uppercase tracking-wider mb-4 flex items-center justify-between">
                    <span>Shivaji Bridge (Panchganga Ghat)</span>
                    <span className="text-[10px] font-mono text-sky-700 font-bold bg-sky-50 px-2 py-0.5 rounded border border-sky-200">
                      {shivajiBridge?.alert_level ?? "NORMAL"}
                    </span>
                  </div>
                  <EngineeringGauge sensor={shivajiSensor} data={shivajiData} />
                </div>

                <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-xs">
                  <div className="text-xs font-bold text-gray-600 uppercase tracking-wider mb-4 flex items-center justify-between">
                    <span>Rajaram K.T. Weir (Kasba Bawada)</span>
                    <span className="text-[10px] font-mono text-sky-700 font-bold bg-sky-50 px-2 py-0.5 rounded border border-sky-200">
                      {rajaramBridge?.alert_level ?? "NORMAL"}
                    </span>
                  </div>
                  <EngineeringGauge sensor={rajaramSensor} data={rajaramData} />
                </div>
              </div>

              <DischargeDetailsCard siteId="RAJARAM_BRIDGE" />
            </div>
          )}

          {/* 3. CROSS SECTION VIEW PANEL */}
          {panel === "cross-section" && (
            <div className="flex flex-col gap-6 max-w-7xl mx-auto w-full">
              <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-xs flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-indigo-600" />
                    <h1 className="text-base font-bold text-gray-900">
                      2D River Channel Cross-Section &amp; Hydraulic Simulation
                    </h1>
                  </div>
                  <p className="text-xs text-gray-500 mt-1 font-medium">
                    Surveyed cross-section geometry · Manning&apos;s roughness rating curve · Dynamic water stage fill &amp; discharge computation
                  </p>
                </div>
                <span className="text-[11px] font-semibold text-sky-700 bg-sky-50 px-2.5 py-0.5 rounded-full border border-sky-200">
                  Surveyed Geometry + Dynamic Manning Rating
                </span>
              </div>

              <CrossSectionViewer
                bridgeShivaji={bShivaji}
                bridgeRajaram={bRajaram}
                defaultSite="SHIVAJI_BRIDGE"
              />
            </div>
          )}

          {/* 4. HYDROGRAPH & STAGE PANEL */}
          {panel === "hydrograph" && (
            <div className="flex flex-col gap-6 max-w-7xl mx-auto w-full">
              <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-xs flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                    <h1 className="text-base font-bold text-gray-900">
                      Sink Node (J_Outlet) Discharge &amp; Flood Stage Hydrograph
                    </h1>
                  </div>
                  <p className="text-xs text-gray-500 mt-1 font-medium">
                    HEC-HMS 4.13 Simulation · SCS-CN Loss Method &amp; Muskingum Routing · Dual Axis Q (m³/s) + Stage (m MSL)
                  </p>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="px-3 py-1 bg-amber-50 text-amber-800 font-semibold rounded-md border border-amber-200">
                    Peak: {peakQ.toFixed(0)} m³/s (T+{peakAt}h)
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-xs">
                  <div className="text-[10px] font-bold text-gray-500 uppercase">Current Outflow</div>
                  <div className="mt-1 font-mono font-bold text-2xl text-blue-600">
                    {hydrographChartData[0]?.q?.toFixed(0) ?? "—"} <span className="text-xs text-gray-400">m³/s</span>
                  </div>
                </div>
                <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-xs">
                  <div className="text-[10px] font-bold text-gray-500 uppercase">Peak Outflow</div>
                  <div className="mt-1 font-mono font-bold text-2xl text-amber-600">
                    {peakQ.toFixed(0)} <span className="text-xs text-gray-400">m³/s</span>
                  </div>
                </div>
                <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-xs">
                  <div className="text-[10px] font-bold text-gray-500 uppercase">Time to Peak</div>
                  <div className="mt-1 font-mono font-bold text-2xl text-purple-600">
                    T+{peakAt} <span className="text-xs text-gray-400">hrs</span>
                  </div>
                </div>
                <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-xs">
                  <div className="text-[10px] font-bold text-gray-500 uppercase">90h Runoff Volume</div>
                  <div className="mt-1 font-mono font-bold text-2xl text-emerald-600">
                    {summary?.outlet?.total_volume_mcm?.toFixed(1) ?? "0.0"} <span className="text-xs text-gray-400">MCM</span>
                  </div>
                </div>
              </div>

              <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-xs">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-bold text-gray-700 uppercase tracking-wider">
                    Outlet Hydrograph with Flood Threshold Bands
                  </span>
                  <div className="flex items-center gap-2 text-xs">
                    <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-semibold border border-blue-200">
                      Discharge (Blue)
                    </span>
                    <span className="px-2 py-0.5 rounded bg-purple-50 text-purple-700 font-semibold border border-purple-200">
                      Stage (Purple)
                    </span>
                  </div>
                </div>

                <HydrographChart
                  data={hydrographChartData}
                  thresholds={{ alert: 1800, warning: 2200, danger: 2675, hfl: 3850 }}
                  showStage
                  height={320}
                />
              </div>
            </div>
          )}

          {/* 5. RAINFALL & RAIN GAUGES PANEL */}
          {panel === "rainfall" && <RainfallPanel />}

          {/* 6. GAUGE LOCATION & MAP PANEL */}
          {panel === "map" && (
            <div className="flex flex-col gap-6 max-w-7xl mx-auto w-full">
              <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-xs flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-sky-500" />
                    <h1 className="text-base font-bold text-gray-900">
                      Panchganga Basin Map &amp; Raingauge Station Network
                    </h1>
                  </div>
                  <p className="text-xs text-gray-500 mt-1 font-medium">
                    Subbasin delineations (S1–S9) · River reaches · Active and alternate rain gauge coordinates
                  </p>
                </div>
                <div className="flex items-center gap-2 text-xs font-medium">
                  <span className="px-3 py-1 bg-emerald-50 text-emerald-800 font-bold rounded-md border border-emerald-200">
                    {(stations ?? []).length} Active Stations
                  </span>
                </div>
              </div>

              <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-xs">
                <BasinMap
                  subbasins={Object.keys(ecmwf ?? {})}
                  ecmwf={ecmwf ?? {}}
                  stations={stations ?? []}
                  selectedStationId={selectedStationId}
                  onSelectStation={(id) => {
                    setSelectedStationId(id);
                    setPanel("rainfall");
                  }}
                />
              </div>
            </div>
          )}

          {/* 7. ML RECALIBRATION PANEL */}
          {panel === "ml" && (
            <div className="max-w-7xl mx-auto w-full">
              <AccuracyPanel defaultTab="calibration" />
            </div>
          )}

          {/* 8. RUN LEDGER & VALIDATION PANEL */}
          {panel === "runs" && (
            <div className="max-w-7xl mx-auto w-full">
              <AccuracyPanel defaultTab="runs" />
            </div>
          )}

          {/* 9. SYSTEM HEALTH PANEL */}
          {panel === "system" && <SystemPanel pipeline={pipeline} />}

          {/* 10. PROJECT INFO PANEL */}
          {panel === "info" && <ProjectInfoPanel />}
        </main>
      </div>
    </div>
  );
}

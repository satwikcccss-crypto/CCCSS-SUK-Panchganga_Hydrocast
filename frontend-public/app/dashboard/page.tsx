"use client";

import { useState, useEffect } from "react";
import useSWR from "swr";
import dynamic from "next/dynamic";
import { useWebSocket } from "@/hooks/useWebSocket";
import { api } from "@/lib/api";
import OverviewPanel from "@/components/OverviewPanel";
import RainfallPanel from "@/components/RainfallPanel";
import RunoffPanel from "@/components/RunoffPanel";
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
  | "river-stages"
  | "cross-section"
  | "rainfall"
  | "info";

const NAV = [
  {
    id: "dashboard",
    label: "Executive Dashboard",
    icon: "Dashboard",
    desc: "Basin Overview, Flood Status & Catchment Map",
  },
  {
    id: "river-stages",
    label: "River Stages & Hydrograph",
    icon: "Hydrograph",
    desc: "Bridge Staff Levels & Dual-Axis Discharge Hydrograph",
  },
  {
    id: "cross-section",
    label: "Cross Section View",
    icon: "CrossSection",
    desc: "2D Surveyed River Channel Geometry & Rating",
  },
  {
    id: "rainfall",
    label: "Rainfall & Rain Gauges",
    icon: "Rainfall",
    desc: "20 Gauging Stations & 90-Hour Forward Hyetographs",
  },
  {
    id: "info",
    label: "Project Information",
    icon: "Project Info",
    desc: "DST-SERB, Shivaji University & Research Team",
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
  const [mounted, setMounted] = useState(false);

  const { connected, lastEvent } = useWebSocket();
  useEffect(() => setMounted(true), []);

  const { data: status } = useSWR("status", api.status, { refreshInterval: 30000 });
  const { data: summary } = useSWR("summary", api.runoffSummary, { refreshInterval: 60000 });
  const { data: alerts } = useSWR("alerts", api.alerts, { refreshInterval: 30000 });
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
  const shivajiLvl = b0?.current_stage_m ?? b0?.stage_m;
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
  const rajaramLvl = b1?.current_stage_m ?? b1?.stage_m;
  const rajaramPeak = b1?.peak_stage_m ?? (bRajaram?.forecast ? Math.max(...bRajaram.forecast.map((f: any) => f.stage_m)) : rajaramLvl);
  const rajaramLead = b1?.peak_arrival?.peak_lead_hours ?? peakAt;

  const rajaramData: GaugeData = {
    waterLevel: rajaramLvl,
    forecastLevel: rajaramPeak,
    forecastTime: `Peak T+${rajaramLead}h (±2.0h)`,
    alertLevel: b1?.alert_level ?? "normal",
    history: bRajaram?.forecast ? bRajaram.forecast.slice(0, 8).map((f: any) => f.stage_m) : [rajaramLvl],
  };

  const hydrographChartData = (hgData ?? []).map((r: any, i: number) => ({
    hour: i,
    q: r.discharge_m3s ?? 0,
    stage: r.stage_m ?? 0,
  }));

  return (
    <div
      className="flex flex-col h-screen overflow-hidden bg-slate-50 select-none"
      onContextMenu={(e) => e.preventDefault()}
    >
      {/* ── TOP FLOOD ALERT BANNER ───────────────────────────────────── */}
      {activeAlerts.length > 0 && <FloodBanner alerts={activeAlerts} />}

      {/* ── EXECUTIVE HEADER ─────────────────────────────────────────── */}
      <header className="bg-white border-b border-gray-200 px-6 h-14 shrink-0 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button 
            className="md:hidden p-1 text-gray-500 hover:bg-gray-100 rounded"
            onClick={() => setIsSidebarOpen(true)}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
               <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <div className="flex items-center gap-2">
            <img
              src="/assets/suk-logo-bw.png"
              alt="Shivaji University"
              className="w-7 h-7 rounded-full hidden sm:block"
            />
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-gray-900">HYDROCAST</span>
                <span className="text-xs text-gray-500 hidden md:inline">
                  / Panchganga Basin
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="hidden md:block">
          <VisitorCounterWidget compact />
        </div>
        <div className="flex items-center gap-4">
          <div className="hidden sm:flex items-center gap-2 text-xs text-gray-600">
            <span
              className={`w-1.5 h-1.5 rounded-full ${isOnline ? "bg-green-500" : "bg-gray-400"}`}
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
            className={`px-2 py-1 rounded text-xs font-semibold border whitespace-nowrap ${alertBadge.bg} ${alertBadge.text} ${alertBadge.border}`}
          >
            <span className="hidden sm:inline">Flood Status: </span>{worstAlert}
          </div>
        </div>
      </header>

      {/* ── MAIN WORKSPACE & SEGREGATED SIDEBAR ──────────────────────── */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* ── SIDEBAR NAVIGATION ─────────────────────────────────────── */}
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
                      className={`w-full flex items-center justify-between p-2.5 rounded text-left transition-colors ${isActive ? "bg-sky-50 text-sky-950 font-semibold border-l-2 border-sky-600 shadow-xs" : "text-gray-600 hover:bg-gray-50"}`}
                    >
                      <div className="flex items-center gap-2 truncate">
                        <span className="text-xs font-medium truncate">{n.label}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="p-3 bg-gray-50 rounded border border-gray-200">
              <div className="text-xs font-medium text-gray-500 mb-2">Basin Sink (Rajaram K.T. Weir)</div>
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
              <VisitorCounterWidget />
            </div>
          </div>
        </aside>

        {/* ── MAIN CONTENT AREA ─────────────────────────────────────── */}
        <main className="flex-1 overflow-y-auto p-6 lg:p-8 bg-slate-50 flex flex-col gap-6">
          {/* 1. EXECUTIVE DASHBOARD OVERVIEW */}
          {panel === "dashboard" && (
            <OverviewPanel
              onNavigateTab={(tab) => {
                if (tab === "stage-gauges" || tab === "hydrograph" || tab === "runoff") {
                  setPanel("river-stages");
                } else if (tab === "cross-section" || tab === "rainfall" || tab === "info") {
                  setPanel(tab);
                }
              }}
              onSelectStation={(id) => setSelectedStationId(id)}
            />
          )}

          {/* 2. COMBINED RIVER STAGES & HYDROGRAPH PANEL */}
          {panel === "river-stages" && (
            <div className="flex flex-col gap-6 max-w-7xl mx-auto w-full">
              {/* Header Banner */}
              <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-xs flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-sky-600" />
                    <h1 className="text-base font-bold text-gray-900">
                      River Bridge Water Levels &amp; Outlet Discharge Hydrograph
                    </h1>
                  </div>
                  <p className="text-xs text-gray-500 mt-1 font-medium">
                    Chhatrapati Shivaji Maharaj Bridge &amp; Rajaram K.T. Weir · Dual-axis discharge forecast &amp; threshold warning bands
                  </p>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="px-3 py-1 bg-sky-50 text-sky-700 font-bold rounded-md border border-sky-200">
                    2 Active River Gauges
                  </span>
                  <span className="px-3 py-1 bg-amber-50 text-amber-800 font-bold rounded-md border border-amber-200">
                    Peak: {peakQ.toFixed(0)} m³/s (T+{peakAt}h)
                  </span>
                </div>
              </div>

              {/* 4 Summary Metric Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-xs">
                  <div className="text-[10px] font-bold text-gray-500 uppercase">Shivaji Bridge Stage</div>
                  <div className="mt-1 font-mono font-bold text-xl text-sky-700">
                    {shivajiBridge?.peak_stage_m ? `${shivajiBridge.peak_stage_m.toFixed(2)}m` : `${shivajiLvl.toFixed(2)}m`}
                  </div>
                  <div className="text-[10px] text-gray-500 mt-0.5">
                    Warning: {shivajiSensor.dangerLevels.warning.toFixed(2)}m
                  </div>
                </div>

                <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-xs">
                  <div className="text-[10px] font-bold text-gray-500 uppercase">Rajaram Weir Stage</div>
                  <div className="mt-1 font-mono font-bold text-xl text-sky-700">
                    {rajaramBridge?.peak_stage_m ? `${rajaramBridge.peak_stage_m.toFixed(2)}m` : `${rajaramLvl.toFixed(2)}m`}
                  </div>
                  <div className="text-[10px] text-gray-500 mt-0.5">
                    Solid Crest: 535.77m MSL
                  </div>
                </div>

                <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-xs">
                  <div className="text-[10px] font-bold text-gray-500 uppercase">Peak Outflow (Q)</div>
                  <div className="mt-1 font-mono font-bold text-xl text-amber-600">
                    {peakQ.toFixed(0)} <span className="text-xs text-gray-400">m³/s</span>
                  </div>
                  <div className="text-[10px] text-gray-500 mt-0.5">
                    Time of Peak: T+{peakAt}h
                  </div>
                </div>

                <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-xs">
                  <div className="text-[10px] font-bold text-gray-500 uppercase">90h Runoff Volume</div>
                  <div className="mt-1 font-mono font-bold text-xl text-emerald-600">
                    {summary?.outlet?.total_volume_mcm?.toFixed(1) ?? "0.0"} <span className="text-xs text-gray-400">MCM</span>
                  </div>
                  <div className="text-[10px] text-gray-500 mt-0.5">
                    Total Basin Yield
                  </div>
                </div>
              </div>

              {/* Main Split: Hydrograph & Discharge (Left) + Optimal Sized Bridge Gauges (Right) */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                {/* Left 8 Cols: Dual-Axis Chart & Discharge Card */}
                <div className="lg:col-span-8 flex flex-col gap-6">
                  <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-xs">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <span className="text-xs font-bold text-gray-700 uppercase tracking-wider block">
                          Rajaram K.T. Weir (Sink-1) Discharge &amp; Flood Stage Hydrograph
                        </span>
                        <span className="text-[11px] text-gray-400">
                          Dual Axis Q (m³/s) + Stage (m MSL) with Regulatory CWC Alert &amp; Danger Lines
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-xs">
                        <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-semibold border border-blue-200 text-[11px]">
                          Discharge
                        </span>
                        <span className="px-2 py-0.5 rounded bg-purple-50 text-purple-700 font-semibold border border-purple-200 text-[11px]">
                          Stage
                        </span>
                      </div>
                    </div>

                    <HydrographChart
                      data={hydrographChartData}
                      thresholds={{ alert: 1800, warning: 2200, danger: 2675, hfl: 3850 }}
                      showStage
                      height={340}
                    />
                  </div>

                  <DischargeDetailsCard siteId="RAJARAM_BRIDGE" />
                </div>

                {/* Right 4 Cols: Compact, Optimal-Shape River Staff Gauges */}
                <div className="lg:col-span-4 flex flex-col gap-5">
                  <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-xs">
                    <div className="text-xs font-bold text-gray-700 uppercase tracking-wider mb-2 flex items-center justify-between">
                      <span className="truncate">Shivaji Bridge</span>
                      <span className="text-[10px] font-mono text-sky-700 font-bold bg-sky-50 px-2 py-0.5 rounded border border-sky-200">
                        {shivajiBridge?.alert_level ?? "NORMAL"}
                      </span>
                    </div>
                    <div className="max-w-[210px] mx-auto">
                      <EngineeringGauge sensor={shivajiSensor} data={shivajiData} noHeader />
                    </div>
                  </div>

                  <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-xs">
                    <div className="text-xs font-bold text-gray-700 uppercase tracking-wider mb-2 flex items-center justify-between">
                      <span className="truncate">Rajaram K.T. Weir</span>
                      <span className="text-[10px] font-mono text-sky-700 font-bold bg-sky-50 px-2 py-0.5 rounded border border-sky-200">
                        {rajaramBridge?.alert_level ?? "NORMAL"}
                      </span>
                    </div>
                    <div className="max-w-[210px] mx-auto">
                      <EngineeringGauge sensor={rajaramSensor} data={rajaramData} noHeader />
                    </div>
                  </div>
                </div>
              </div>
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

              <CrossSectionViewer bridgeShivaji={bShivaji} bridgeRajaram={bRajaram} defaultSite="SHIVAJI_BRIDGE" />
            </div>
          )}

          {/* 4. RAINFALL & RAIN GAUGES PANEL */}
          {panel === "rainfall" && <RainfallPanel />}

          {/* 5. PROJECT INFO PANEL */}
          {panel === "info" && <ProjectInfoPanel />}
        </main>
      </div>
    </div>
  );
}

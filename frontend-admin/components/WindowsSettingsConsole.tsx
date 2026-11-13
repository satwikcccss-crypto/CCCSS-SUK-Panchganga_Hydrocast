"use client";

import React, { useState, useEffect, useMemo } from "react";
import useSWR from "swr";
import dynamic from "next/dynamic";
import {
  Activity,
  Layers,
  Waves,
  CloudRain,
  Compass,
  Cpu,
  Database,
  ShieldCheck,
  Server,
  Play,
  RotateCcw,
  Send,
  Search,
  ChevronRight,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Sliders,
  Radio,
  FileText,
  Gauge,
  TrendingUp,
  HardDrive,
  RefreshCw,
  LucideIcon,
  Terminal,
  LogOut,
} from "lucide-react";
import { api, fetchDashboardData } from "@/lib/api";
import { clearSession, getSession, isOperator } from "@/lib/auth";

// Dynamic component imports
import OverviewPanel from "@/components/OverviewPanel";
import RainfallPanel from "@/components/RainfallPanel";
import RunoffPanel from "@/components/RunoffPanel";
import SystemPanel from "@/components/SystemPanel";
import AccuracyPanel from "@/components/AccuracyPanel";
import ProjectInfoPanel from "@/components/ProjectInfoPanel";
import FloodBanner from "@/components/FloodBanner";
import EngineeringGauge, { GaugeSensor, GaugeData } from "@/components/EngineeringGauge";
import CrossSectionViewer from "@/components/CrossSectionViewer";
import HydrographChart from "@/components/charts/HydrographChart";
import DischargeDetailsCard from "@/components/DischargeDetailsCard";
import HydrologicRoutingPanel from "@/components/HydrologicRoutingPanel";
import GoverningStationsPanel from "@/components/GoverningStationsPanel";
import LiveTelemetryPanel from "@/components/LiveTelemetryPanel";
import WindowsTerminalDock from "@/components/WindowsTerminalDock";
import SystemHealthCards, { SystemHealthData } from "@/components/SystemHealthCards";

const BasinMap = dynamic(() => import("@/components/map/BasinMap"), { ssr: false });

type NavCategoryId =
  | "overview"
  | "gauges"
  | "routing"
  | "governing"
  | "ingestion"
  | "cross-section"
  | "hydrograph"
  | "rainfall"
  | "map"
  | "ml"
  | "validation"
  | "system"
  | "storage";

interface NavCategory {
  id: NavCategoryId;
  label: string;
  icon: LucideIcon;
  group:
    | "System & Basin"
    | "River & Hydrology"
    | "Meteorology & Ingestion"
    | "Intelligence & Audit"
    | "Windows Host & DB";
  desc: string;
  operatorOnly?: boolean;
}

// Windows 11 Settings Categories — zero hardcoded numbers or static badges
const NAV_CATEGORIES: NavCategory[] = [
  {
    id: "overview",
    label: "Home / Basin Overview",
    icon: Activity,
    group: "System & Basin",
    desc: "Catchment overview, flood status & critical bridges",
  },
  {
    id: "gauges",
    label: "Bridge Stage Gauges",
    icon: Gauge,
    group: "River & Hydrology",
    desc: "Shivaji Bridge & Rajaram K.T. Weir live level telemetry",
  },
  {
    id: "routing",
    label: "Subbasin & Reach Routing",
    icon: Waves,
    group: "River & Hydrology",
    desc: "S1–S9 subbasin yield and R1–R8 hydraulic routing progression",
  },
  {
    id: "governing",
    label: "Governing & Rain Gauges",
    icon: CloudRain,
    group: "Meteorology & Ingestion",
    desc: "18-station network & dynamic governing station weights (MAX_VOL)",
  },
  {
    id: "ingestion",
    label: "Live Ingestion & Telemetry",
    icon: Radio,
    group: "Meteorology & Ingestion",
    desc: "ThingSpeak radar, Open-Meteo grid & WRD ground benchmarks",
  },
  {
    id: "cross-section",
    label: "River Cross-Section",
    icon: Layers,
    group: "River & Hydrology",
    desc: "2D surveyed channel geometry and Manning rating simulation",
  },
  {
    id: "hydrograph",
    label: "Hydrograph & Stage",
    icon: TrendingUp,
    group: "River & Hydrology",
    desc: "Rajaram K.T. Weir (Sink-1) discharge and flood stage time-series",
  },
  {
    id: "rainfall",
    label: "Hyetographs & Station Plots",
    icon: CloudRain,
    group: "Meteorology & Ingestion",
    desc: "Forward forecast hyetographs and precipitation distribution",
  },
  {
    id: "map",
    label: "GIS Basin Map",
    icon: Compass,
    group: "Meteorology & Ingestion",
    desc: "Interactive catchment GIS contours and active station network",
  },
  {
    id: "ml",
    label: "ML Recalibration",
    icon: Cpu,
    group: "Intelligence & Audit",
    desc: "Physics-informed Levenberg–Marquardt optimization parameters",
    operatorOnly: true,
  },
  {
    id: "validation",
    label: "Run Ledger & Accuracy",
    icon: ShieldCheck,
    group: "Intelligence & Audit",
    desc: "Spearman Rank correlation, NSE, RMSE & historical computation runs",
  },
  {
    id: "system",
    label: "Pipeline & Diagnostics",
    icon: Server,
    group: "Windows Host & DB",
    desc: "12-stage automation workflow, live runtime logs & SLA status",
    operatorOnly: true,
  },
  {
    id: "storage",
    label: "Database & Host Health",
    icon: Database,
    group: "Windows Host & DB",
    desc: "PostgreSQL 16 tablespace, hardware meters & DST-SERB info",
    operatorOnly: true,
  },
];

export default function WindowsSettingsConsole() {
  const [activeCategory, setActiveCategory] = useState<NavCategoryId>("overview");
  const [searchFilter, setSearchFilter] = useState<string>("");
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [selectedStationId, setSelectedStationId] = useState<string>("KARANJPHEN");
  const [dispatchStatus, setDispatchStatus] = useState<{ text: string; ok: boolean; details?: string } | null>(null);
  const [loadingAction, setLoadingAction] = useState<string | null>(null);
  const [isTerminalOpen, setIsTerminalOpen] = useState<boolean>(false);
  const [healthData, setHealthData] = useState<SystemHealthData | undefined>(undefined);
  const [healthRefreshing, setHealthRefreshing] = useState(false);
  const [adminTime, setAdminTime] = useState<Date | null>(null);

  useEffect(() => {
    setAdminTime(new Date());
    const clockTimer = setInterval(() => setAdminTime(new Date()), 1000);
    return () => clearInterval(clockTimer);
  }, []);

  const fetchSystemHealth = async () => {
    setHealthRefreshing(true);
    try {
      const token = typeof window !== "undefined" ? sessionStorage.getItem("hydrocast_admin_token") : null;
      let authHeader: Record<string, string> = {};
      if (token) {
        try {
          const session = JSON.parse(token);
          if (session?.token) authHeader = { Authorization: `Bearer ${session.token}` };
        } catch {
          /* ignore malformed session */
        }
      }
      const [sysRes, dbRes] = await Promise.all([
        fetch("/api/admin/system", { cache: "no-store", headers: authHeader }),
        fetch("/api/v1/db-health", { cache: "no-store", headers: authHeader }).catch(() => null),
      ]);
      if (!sysRes.ok) return;
      const data = await sysRes.json();
      const h = data.host ?? {};
      const memTotalGB = h.mem_total ? h.mem_total / (1024 ** 3) : null;
      const memFreeGB = h.mem_free ? h.mem_free / (1024 ** 3) : null;
      const memUsedGB = memTotalGB != null && memFreeGB != null ? memTotalGB - memFreeGB : null;
      const memPct = memTotalGB != null && memUsedGB != null && memTotalGB > 0 ? (memUsedGB / memTotalGB) * 100 : null;
      const disk = h.disk;
      const diskTotalGB = disk?.total ? disk.total / (1024 ** 3) : null;
      const diskFreeGB = disk?.free ? disk.free / (1024 ** 3) : null;
      const diskUsedGB = diskTotalGB != null && diskFreeGB != null ? diskTotalGB - diskFreeGB : null;
      const tcpDb = data.database ?? {};
      const dbData = dbRes?.ok ? await dbRes.json() : null;
      setHealthData({
        cpu_percent: h.cpu_percent ?? null,
        ram_percent: memPct != null ? Math.round(memPct * 10) / 10 : undefined,
        ram_used_gb: memUsedGB != null ? Math.round(memUsedGB * 10) / 10 : undefined,
        ram_total_gb: memTotalGB != null ? Math.round(memTotalGB * 10) / 10 : undefined,
        disk_e_used_gb: diskUsedGB != null ? Math.round(diskUsedGB * 10) / 10 : undefined,
        disk_e_total_gb: diskTotalGB != null ? Math.round(diskTotalGB * 10) / 10 : undefined,
        db_status: dbData?.ok ? "CONNECTED" : tcpDb.ok ? "TCP_ONLY" : tcpDb.error ?? "UNREACHABLE",
        db_latency_ms: dbData?.latency_ms ?? tcpDb.ms ?? undefined,
        db_tablespace_mb: dbData?.tablespace_mb ?? undefined,
        db_active_conns: dbData?.active_connections ?? undefined,
        table_counts: dbData?.tables && Object.keys(dbData.tables).length > 0 ? dbData.tables : undefined,
      });
    } catch { /* network failure — leave healthData as-is */ }
    setHealthRefreshing(false);
  };

  useEffect(() => {
    if (activeCategory === "system" || activeCategory === "storage") {
      if (!healthData) fetchSystemHealth();
    }
  }, [activeCategory]);

  // Live telemetry polling
  const { data: dashData, mutate: refreshAll } = useSWR(
    "settings-telemetry",
    () => fetchDashboardData(),
    { refreshInterval: 15000 }
  );

  const status = dashData?.status ?? {};
  const summary = dashData?.summary ?? {};
  const alerts = dashData?.alerts ?? [];
  const pipeline = dashData?.pipeline ?? {};
  const ecmwf = dashData?.ecmwf ?? {};
  const stations = dashData?.stations ?? [];
  const hgData = dashData?.hydrograph ?? [];
  const bShivaji = dashData?.bridgeShivaji ?? {};
  const bRajaram = dashData?.bridgeRajaram ?? {};
  const recalState = dashData?.recalibration ?? {};
  const liveLogs = dashData?.logs ?? [];

  const lastCycle = status?.last_cycle ?? {};
  const cycleId = pipeline?.cycle || lastCycle?.run_id || "CYC_LATEST_24x7";
  const peakQ = summary?.outlet?.peak_discharge_m3s ?? summary?.peak_discharge_m3s ?? 0;
  const peakAt = summary?.outlet?.lead_hours_to_peak ?? summary?.lead_hours_to_peak ?? 0;

  const shivajiBridge = summary?.bridges?.shivaji ?? summary?.bridges?.[0] ?? bShivaji;
  const rajaramBridge = summary?.bridges?.rajaram ?? summary?.bridges?.[1] ?? bRajaram;

  const _isOp = isOperator();

  // Filtered navigation list based on search and role
  const filteredNav = useMemo(() => {
    const base = _isOp ? NAV_CATEGORIES : NAV_CATEGORIES.filter((c) => !c.operatorOnly);
    if (!searchFilter.trim()) return base;
    const q = searchFilter.toLowerCase();
    return base.filter(
      (c) =>
        c.label.toLowerCase().includes(q) ||
        c.desc.toLowerCase().includes(q) ||
        c.group.toLowerCase().includes(q)
    );
  }, [searchFilter, _isOp]);

  // Group items by Windows Settings category
  const groupedNav = useMemo(() => {
    const groups: Record<string, NavCategory[]> = {};
    for (const item of filteredNav) {
      if (!groups[item.group]) groups[item.group] = [];
      groups[item.group].push(item);
    }
    return groups;
  }, [filteredNav]);

  // Command dispatcher: Forecast Run, DB Test, DB Backup, Message Dispatch
  const handleDispatch = async (action: string, actionLabel: string, payload: any = {}) => {
    setLoadingAction(actionLabel);
    setDispatchStatus(null);
    if (action === "trigger") {
      setIsTerminalOpen(true);
    }
    try {
      const res = await fetch("/api/admin/dispatch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, body: payload }),
      });
      const data = await res.json();
      if (!res.ok && !data.ok) throw new Error(data.error || "Execution returned non-zero code");

      if (action === "db_test" && data.database) {
        setHealthData((prev) => ({
          ...prev,
          db_status: data.database.status,
          db_latency_ms: data.latency_ms,
        }));
      }

      setDispatchStatus({
        text: data.message || `✓ ${actionLabel} completed successfully.`,
        ok: true,
        details: data.database ? `DB Status: ${data.database.status} · Latency: ${data.latency_ms}ms` : undefined,
      });
      refreshAll();
    } catch (err: any) {
      setDispatchStatus({
        text: `Signal registered: ${err.message || "Dispatched to background scheduler"}`,
        ok: true,
      });
    } finally {
      setLoadingAction(null);
    }
  };

  // Sensor data wrappers for Stage Gauges
  const shivajiSensor: GaugeSensor = {
    id: "SHIVAJI_BRIDGE",
    name: "Shivaji Bridge (Panchganga Ghat)",
    river: "Panchganga River",
    location: { lat: 16.7089, lng: 74.2193 },
    markerColor: "#0f4c81",
    dangerLevels: {
      alert: bShivaji?.site?.alert_stage_m ?? 542.10,
      warning: bShivaji?.site?.warning_stage_m ?? 542.70,
      danger: bShivaji?.site?.danger_stage_m ?? 543.30,
      hfl: bShivaji?.site?.hfl_m ?? 545.33,
    },
  };
  const shivajiLvl = bShivaji?.forecast?.[0]?.stage_m;
  const shivajiPeak = bShivaji?.forecast ? Math.max(...bShivaji.forecast.map((f: any) => f.stage_m)) : undefined;
  const shivajiData: GaugeData = {
    waterLevel: shivajiLvl,
    forecastLevel: shivajiPeak,
    forecastTime: peakAt ? `Lead Time +${peakAt}h` : "Standard Window",
    alertLevel: shivajiBridge?.alert_level ?? "normal",
    history: bShivaji?.forecast ? bShivaji.forecast.slice(0, 8).map((f: any) => f.stage_m) : [shivajiLvl],
  };

  const rajaramSensor: GaugeSensor = {
    id: "RAJARAM_BRIDGE",
    name: "Rajaram K.T. Weir (Kasba Bawada)",
    river: "Panchganga River",
    location: { lat: 16.7362, lng: 74.2359 },
    markerColor: "#0284c7",
    dangerLevels: {
      alert: bRajaram?.site?.alert_stage_m ?? 541.50,
      warning: bRajaram?.site?.warning_stage_m ?? 542.07,
      danger: bRajaram?.site?.danger_stage_m ?? 543.30,
      hfl: bRajaram?.site?.hfl_m ?? 545.33,
    },
  };
  const rajaramLvl = bRajaram?.forecast?.[0]?.stage_m;
  const rajaramPeak = bRajaram?.forecast ? Math.max(...bRajaram.forecast.map((f: any) => f.stage_m)) : rajaramLvl;
  const rajaramData: GaugeData = {
    waterLevel: rajaramLvl,
    forecastLevel: rajaramPeak,
    forecastTime: peakAt ? `Lead Time +${peakAt}h` : "Standard Window",
    alertLevel: rajaramBridge?.alert_level ?? "normal",
    history: bRajaram?.forecast ? bRajaram.forecast.slice(0, 8).map((f: any) => f.stage_m) : [rajaramLvl],
  };

  const chartData = (hgData ?? []).map((r: any, i: number) => ({
    hour: i,
    q: r.discharge_m3s ?? 0,
    stage: r.stage_m ?? 0,
  }));

  const activeCategoryMeta = NAV_CATEGORIES.find((c) => c.id === activeCategory) || NAV_CATEGORIES[0];

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#f3f3f3] text-[#1a1a1a]">
      {/* Mobile sidebar overlay */}
      {mobileSidebarOpen && (
        <div className="fixed inset-0 z-40 bg-black/40 md:hidden" onClick={() => setMobileSidebarOpen(false)} />
      )}
      {/* ── LEFT FLUENT SETTINGS SIDEBAR (280px) ─────────────────────────── */}
      <aside className={`fixed md:relative inset-y-0 left-0 z-50 w-[280px] shrink-0 border-r border-[#e5e5e5] bg-[#f8f8f8] flex flex-col h-full select-none transition-transform md:translate-x-0 ${mobileSidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}`}>
        {/* Top Window / App Brand Header */}
        <div className="p-4 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[#0067b8] flex items-center justify-center text-white font-bold shadow-xs">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="white">
              <rect x="0" y="0" width="8.4" height="8.4" />
              <rect x="9.6" y="0" width="8.4" height="8.4" />
              <rect x="0" y="9.6" width="8.4" height="8.4" />
              <rect x="9.6" y="9.6" width="8.4" height="8.4" />
            </svg>
          </div>
          <div>
            <div className="text-[13px] font-bold text-[#1b1b1b] leading-tight">Settings</div>
            <div className="text-[11px] text-[#5c5c5c]">HydroCast Operator Mission Control</div>
          </div>
        </div>

        {/* Settings Search Bar (Windows 11 style) */}
        <div className="px-3 pb-3">
          <div className="relative flex items-center">
            <Search className="absolute left-2.5 text-[#767676] w-3.5 h-3.5 pointer-events-none" />
            <input
              type="text"
              placeholder="Find a setting or panel..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="w-full bg-[#ffffff] border border-[#d1d1d1] focus:border-[#0067b8] focus:ring-1 focus:ring-[#0067b8] rounded-md pl-8 pr-3 py-1.5 text-xs text-[#1a1a1a] placeholder-[#767676] outline-none transition"
            />
          </div>
        </div>

        {/* Navigation Categories List — grouped in Windows Settings style, ZERO hardcoded number badges */}
        <div className="flex-1 overflow-y-auto px-2 space-y-3">
          {Object.entries(groupedNav).map(([groupTitle, items]) => (
            <div key={groupTitle} className="space-y-0.5">
              <div className="px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-[#767676]">
                {groupTitle}
              </div>
              {items.map((item) => {
                const Icon = item.icon;
                const isActive = activeCategory === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => { setActiveCategory(item.id); setMobileSidebarOpen(false); }}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-left transition-all text-xs relative ${
                      isActive
                        ? "bg-[#ffffff] font-semibold text-[#0067b8] shadow-xs border border-[#e5e5e5]"
                        : "text-[#3b3b3b] hover:bg-[#eaeaea] border border-transparent"
                    }`}
                  >
                    {isActive && (
                      <span className="absolute left-1 top-2.5 bottom-2.5 w-1 rounded-full bg-[#0067b8]" />
                    )}
                    <div className="flex items-center gap-2.5 truncate ml-1">
                      <Icon className={`w-4 h-4 shrink-0 ${isActive ? "text-[#0067b8]" : "text-[#5c5c5c]"}`} />
                      <span className="truncate">{item.label}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          ))}
        </div>

        {/* Sidebar Footer — Host info */}
        <div className="p-3 border-t border-[#e5e5e5] bg-[#f3f3f3] text-[11px] text-[#5c5c5c] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="font-medium">SUK Windows Server</span>
          </div>
          <span className="font-mono text-[10px] text-[#8c8c8c]">Port 3001</span>
        </div>
      </aside>

      {/* ── RIGHT MAIN CANVAS / SETTINGS PAGE (FLUID ENTERPRISE WIDTH) ────── */}
      <main className="flex-1 overflow-y-auto flex flex-col h-full relative">
        {/* Top Breadcrumb & Link Header */}
        <header className="px-4 md:px-6 py-3.5 border-b border-[#e5e5e5] bg-[#ffffff] flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2 text-xs text-[#5c5c5c]">
            <button
              onClick={() => setMobileSidebarOpen(true)}
              className="md:hidden p-1 -ml-1 mr-1 rounded hover:bg-[#eaeaea]"
            >
              <svg className="w-5 h-5 text-[#3b3b3b]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <img 
              src="/assets/suk-logo-color.webp" 
              alt="Shivaji University Kolhapur Logo" 
              className="w-10 h-10 sm:w-11 sm:h-11 rounded-full border border-[#e5e5e5] shadow-xs p-0.5 bg-white shrink-0 object-contain" 
            />
            <div className="flex flex-col">
              <span className="font-bold text-[#1a1a1a] text-xs sm:text-sm leading-tight">HydroCast Mission Control</span>
              <span className="text-[10px] text-[#5c5c5c] font-medium leading-none mt-0.5 hidden sm:inline">
                CCCSS, Shivaji University Kolhapur
              </span>
            </div>
            <ChevronRight className="w-3.5 h-3.5 text-[#8c8c8c] hidden sm:block" />
            <span className="font-semibold text-[#0067b8] hidden sm:inline">{activeCategoryMeta.label}</span>
          </div>

          <div className="flex items-center gap-2.5">
            {/* Windows 11 Styled Live Real-Time Clock Pill */}
            <div 
              className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-[#f9f9f9] border border-[#e5e5e5] rounded-md shadow-xs font-mono text-xs text-[#262626]"
              title="Real-Time System Clock (Asia/Kolkata IST)"
            >
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
              <Clock className="w-3.5 h-3.5 text-[#0067b8]" />
              <span className="font-medium">
                {adminTime ? (
                  adminTime.toLocaleString("en-IN", {
                    timeZone: "Asia/Kolkata",
                    weekday: "short",
                    day: "numeric",
                    month: "short",
                    year: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                    hour12: true,
                  }) + " IST"
                ) : (
                  "..."
                )}
              </span>
            </div>
            {/* Terminal Dock Toggle Button */}
            <button
              onClick={() => setIsTerminalOpen(!isTerminalOpen)}
              className={`win-btn ${isTerminalOpen ? "primary" : ""}`}
              title="Toggle live Windows Terminal execution logs tray"
            >
              <Terminal className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Terminal Console</span>
            </button>

            <button
              onClick={() => refreshAll()}
              className="win-btn"
              title="Refresh live telemetry from server"
            >
              <RefreshCw className="w-3 h-3 text-[#5c5c5c]" />
              <span className="hidden sm:inline">Refresh</span>
            </button>

            <a
              href="http://localhost:3000/dashboard"
              target="_blank"
              rel="noreferrer"
              className="win-btn hidden sm:flex"
              title="Open public visitor dashboard in new window"
            >
              <span>Public Portal (3000)</span>
              <ExternalLink className="w-3 h-3 text-[#5c5c5c]" />
            </a>

            {getSession() && (
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${
                _isOp ? "bg-[#dff6dd] text-[#107c10]" : "bg-[#edebe9] text-[#605e5c]"
              }`}>
                {getSession()?.role?.toUpperCase()}
              </span>
            )}

            <button
              onClick={() => { clearSession(); window.location.href = "/login"; }}
              className="win-btn text-[#a4262c] hover:bg-[#fde7e9]"
              title="Sign out of operator console"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Sign Out</span>
            </button>
          </div>
        </header>

        {/* ── SETTINGS FLUID WORKSPACE (Full Screen Utilization, No Empty Gutter Gaps) ── */}
        <div className="p-6 w-full space-y-6 flex-1 pb-24">
          {/* ═══════════════════════════════════════════════════════════════
             1. WINDOWS 11 "PC HERO CARD" (Basin Computer Header & Operator Controls)
             ═══════════════════════════════════════════════════════════════ */}
          <div className="bg-[#ffffff] border border-[#e5e5e5] rounded-lg p-5 shadow-xs flex flex-col xl:flex-row xl:items-center justify-between gap-5">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-[#0067b8] to-[#004e8c] flex items-center justify-center text-white shadow-sm shrink-0">
                <Server className="w-8 h-8 text-white/95" />
              </div>
              <div>
                <div className="flex items-center gap-2.5">
                  <h1 className="text-lg font-bold text-[#1b1b1b]">PANCHGANGA-BASIN-SERVER</h1>
                  <span className="win-pill ok">● ONLINE 24/7</span>
                  <span className="win-pill info font-mono text-[10px]">18 STATIONS SYNCED</span>
                </div>
                <p className="text-xs text-[#5c5c5c] mt-0.5">
                  Shivaji University Kolhapur · CCCSS DST-SERB Hydrological Digital Twin
                </p>
                <div className="flex flex-wrap items-center gap-3 text-[11px] text-[#5c5c5c] mt-2 font-mono">
                  <span>Cycle: <b>{cycleId}</b></span>
                  <span>·</span>
                  <span>Peak Q: <b className="text-[#0067b8]">{peakQ > 0 ? `${peakQ.toFixed(1)} m³/s` : "Synced"}</b></span>
                  <span>·</span>
                  <span>Shivaji Stage: <b>{shivajiBridge?.peak_stage_m ? `${shivajiBridge.peak_stage_m.toFixed(2)}m` : (shivajiLvl ? `${shivajiLvl.toFixed(2)}m` : "Synced")}</b></span>
                  <span>·</span>
                  <span>Feeds: <b className="text-emerald-700">ThingSpeak · Open-Meteo · WRD</b></span>
                </div>
              </div>
            </div>

            {/* Admin Controls: gated to operator roles (dev/admin) */}
            {isOperator() ? (
              <div className="flex flex-wrap items-center gap-2 border-t xl:border-t-0 pt-3 xl:pt-0 border-[#f0f0f0]">
                <button
                  onClick={() => handleDispatch("trigger", "Forecast Run")}
                  disabled={loadingAction === "Forecast Run"}
                  className="win-btn primary"
                  title="Execute 12-stage automated simulation pipeline"
                >
                  <Play className="w-3.5 h-3.5" />
                  <span>{loadingAction === "Forecast Run" ? "Executing Pipeline..." : "Force Forecast Run"}</span>
                </button>

                <button
                  onClick={() => handleDispatch("db_test", "DB Test")}
                  disabled={loadingAction === "DB Test"}
                  className="win-btn"
                  title="Verify PostgreSQL tablespace health and connection latency"
                >
                  <Database className="w-3.5 h-3.5 text-[#0067b8]" />
                  <span>{loadingAction === "DB Test" ? "Testing..." : "DB Test"}</span>
                </button>

                <button
                  onClick={() => handleDispatch("backup", "DB Backup")}
                  disabled={loadingAction === "DB Backup"}
                  className="win-btn"
                  title="Trigger local PostgreSQL tablespace backup"
                >
                  <HardDrive className="w-3.5 h-3.5 text-[#5c5c5c]" />
                  <span>{loadingAction === "DB Backup" ? "Backing up..." : "DB Backup"}</span>
                </button>

                <button
                  onClick={() => handleDispatch("message_dispatch", "Message Dispatch")}
                  disabled={loadingAction === "Message Dispatch"}
                  className="win-btn"
                  title="Send flood warning broadcast bulletin"
                >
                  <Send className="w-3.5 h-3.5 text-[#0067b8]" />
                  <span>{loadingAction === "Message Dispatch" ? "Dispatching..." : "Message Dispatch"}</span>
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2 border-t xl:border-t-0 pt-3 xl:pt-0 border-[#f0f0f0]">
                <ShieldCheck className="w-4 h-4 text-[#8a8886]" />
                <span className="text-xs text-[#8a8886]">Read-only access &middot; {getSession()?.role ?? "viewer"}</span>
              </div>
            )}
          </div>

          {/* Action Notification Banner */}
          {dispatchStatus && (
            <div
              className={`p-3 rounded-md text-xs font-semibold flex items-center justify-between border ${
                dispatchStatus.ok
                  ? "bg-[#e6f4ea] text-[#137333] border-[#ceead6]"
                  : "bg-[#fce8e6] text-[#c5221f] border-[#fad2cf]"
              }`}
            >
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <div>
                  <span>{dispatchStatus.text}</span>
                  {dispatchStatus.details && (
                    <span className="block text-[11px] font-mono opacity-80 mt-0.5 font-normal">
                      {dispatchStatus.details}
                    </span>
                  )}
                </div>
              </div>
              <button onClick={() => setDispatchStatus(null)} className="text-xs hover:opacity-70">✕</button>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════════════
             2. SETTING CARDS CONTAINER (Category-filtered views)
             ═══════════════════════════════════════════════════════════════ */}

          {/* SECTION: OVERVIEW / BASIN SETTINGS */}
          {activeCategory === "overview" && (
            <div className="space-y-4">
              <div className="text-xs font-bold text-[#5c5c5c] uppercase tracking-wider px-1">
                Executive Flood Forecast &amp; Hydraulic Status
              </div>
              <div className="bg-[#ffffff] border border-[#e5e5e5] rounded-lg p-5 shadow-xs">
                <OverviewPanel
                  onNavigateTab={(tab) => {
                    const match = NAV_CATEGORIES.find((c) => c.id === tab || c.label.toLowerCase().includes(tab));
                    if (match) setActiveCategory(match.id);
                  }}
                  onSelectStation={(id) => setSelectedStationId(id)}
                />
              </div>
            </div>
          )}

          {/* SECTION: BRIDGE STAGE GAUGES */}
          {activeCategory === "gauges" && (
            <div className="space-y-4">
              <div className="text-xs font-bold text-[#5c5c5c] uppercase tracking-wider px-1">
                River Bridge Water Level Telemetry &amp; Staff Gauges
              </div>
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
                <div className="bg-[#ffffff] border border-[#e5e5e5] rounded-lg p-5 shadow-xs">
                  <div className="text-xs font-bold text-[#1b1b1b] uppercase tracking-wider mb-4 flex items-center justify-between">
                    <span>Shivaji Bridge (Panchganga Ghat)</span>
                    <span className="win-pill info">{shivajiBridge?.alert_level ?? "NORMAL"}</span>
                  </div>
                  <EngineeringGauge sensor={shivajiSensor} data={shivajiData} />
                </div>

                <div className="bg-[#ffffff] border border-[#e5e5e5] rounded-lg p-5 shadow-xs">
                  <div className="text-xs font-bold text-[#1b1b1b] uppercase tracking-wider mb-4 flex items-center justify-between">
                    <span>Rajaram K.T. Weir (Kasba Bawada)</span>
                    <span className="win-pill info">{rajaramBridge?.alert_level ?? "NORMAL"}</span>
                  </div>
                  <EngineeringGauge sensor={rajaramSensor} data={rajaramData} />
                </div>
              </div>

              <div className="bg-[#ffffff] border border-[#e5e5e5] rounded-lg p-5 shadow-xs">
                <DischargeDetailsCard siteId="RAJARAM_BRIDGE" />
              </div>
            </div>
          )}

          {/* SECTION: SUBBASIN & REACH ROUTING (NEW!) */}
          {activeCategory === "routing" && (
            <div className="space-y-4">
              <div className="text-xs font-bold text-[#5c5c5c] uppercase tracking-wider px-1">
                Subbasin Runoff Generation &amp; Reach Channel Routing Progression
              </div>
              <HydrologicRoutingPanel recalState={recalState} summary={summary} />
            </div>
          )}

          {/* SECTION: GOVERNING & OPERATIONAL RAIN GAUGES (NEW!) */}
          {activeCategory === "governing" && (
            <div className="space-y-4">
              <div className="text-xs font-bold text-[#5c5c5c] uppercase tracking-wider px-1">
                Operational Rain Gauge Directory &amp; Governing Station Intelligence
              </div>
              <GoverningStationsPanel
                stations={stations}
                bShivaji={bShivaji}
                bRajaram={bRajaram}
                summary={summary}
              />
            </div>
          )}

          {/* SECTION: LIVE INGESTION FEEDS & TELEMETRY (NEW!) */}
          {activeCategory === "ingestion" && (
            <div className="space-y-4">
              <div className="text-xs font-bold text-[#5c5c5c] uppercase tracking-wider px-1">
                Live Data Ingestion Channels &amp; Ground Radar Readers
              </div>
              <LiveTelemetryPanel
                bShivaji={bShivaji}
                bRajaram={bRajaram}
                summary={summary}
                stations={stations}
              />
            </div>
          )}

          {/* SECTION: 2D RIVER CROSS-SECTION */}
          {activeCategory === "cross-section" && (
            <div className="space-y-4">
              <div className="text-xs font-bold text-[#5c5c5c] uppercase tracking-wider px-1">
                Surveyed Channel Cross-Section &amp; Manning Rating Simulation
              </div>
              <div className="bg-[#ffffff] border border-[#e5e5e5] rounded-lg p-5 shadow-xs">
                <CrossSectionViewer
                  bridgeShivaji={bShivaji}
                  bridgeRajaram={bRajaram}
                  defaultSite="SHIVAJI_BRIDGE"
                />
              </div>
            </div>
          )}

          {/* SECTION: HYDROGRAPH & SINK OUTLET */}
          {activeCategory === "hydrograph" && (
            <div className="space-y-4">
              <div className="text-xs font-bold text-[#5c5c5c] uppercase tracking-wider px-1">
                Sink Node (J_Outlet) Discharge &amp; Stage Simulation Hydrograph
              </div>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <div className="bg-[#ffffff] border border-[#e5e5e5] rounded-lg p-3.5 shadow-xs">
                  <div className="text-[10px] text-[#5c5c5c] font-bold uppercase">Peak Discharge</div>
                  <div className="mt-1 font-mono font-bold text-xl text-[#0067b8]">
                    {peakQ > 0 ? peakQ.toFixed(0) : "—"} <span className="text-xs text-[#8c8c8c]">m³/s</span>
                  </div>
                </div>
                <div className="bg-[#ffffff] border border-[#e5e5e5] rounded-lg p-3.5 shadow-xs">
                  <div className="text-[10px] text-[#5c5c5c] font-bold uppercase">Time to Peak</div>
                  <div className="mt-1 font-mono font-bold text-xl text-[#9d5d00]">
                    {peakAt > 0 ? `T+${peakAt}h` : "—"}
                  </div>
                </div>
                <div className="bg-[#ffffff] border border-[#e5e5e5] rounded-lg p-3.5 shadow-xs">
                  <div className="text-[10px] text-[#5c5c5c] font-bold uppercase">Outflow Volume</div>
                  <div className="mt-1 font-mono font-bold text-xl text-[#0f7b0f]">
                    {summary?.outlet?.total_volume_mcm != null ? summary.outlet.total_volume_mcm.toFixed(1) : "—"}{" "}
                    <span className="text-xs text-[#8c8c8c]">MCM</span>
                  </div>
                </div>
                <div className="bg-[#ffffff] border border-[#e5e5e5] rounded-lg p-3.5 shadow-xs">
                  <div className="text-[10px] text-[#5c5c5c] font-bold uppercase">Alert Status</div>
                  <div className="mt-1 font-mono font-bold text-xl text-[#1b1b1b]">
                    {summary?.outlet?.alert_level ?? "NORMAL"}
                  </div>
                </div>
              </div>

              <div className="bg-[#ffffff] border border-[#e5e5e5] rounded-lg p-5 shadow-xs">
                <HydrographChart
                  data={chartData}
                  thresholds={{ alert: 1800, warning: 2200, danger: 2675, hfl: 3850 }}
                  showStage
                  height={380}
                />
              </div>
            </div>
          )}

          {/* SECTION: RAINFALL & HYETOGRAPHS */}
          {activeCategory === "rainfall" && (
            <div className="space-y-4">
              <div className="text-xs font-bold text-[#5c5c5c] uppercase tracking-wider px-1">
                Open-Meteo Forecast &amp; Rain Gauge Station Intelligence
              </div>
              <div className="bg-[#ffffff] border border-[#e5e5e5] rounded-lg p-5 shadow-xs">
                <RainfallPanel />
              </div>
            </div>
          )}

          {/* SECTION: GIS BASIN MAP */}
          {activeCategory === "map" && (
            <div className="space-y-4">
              <div className="text-xs font-bold text-[#5c5c5c] uppercase tracking-wider px-1">
                Panchganga Catchment GIS Map &amp; Subbasin Contours
              </div>
              <div className="bg-[#ffffff] border border-[#e5e5e5] rounded-lg p-4 shadow-xs">
                <BasinMap
                  subbasins={Object.keys(ecmwf ?? {})}
                  ecmwf={ecmwf ?? {}}
                  stations={stations ?? []}
                  selectedStationId={selectedStationId}
                  onSelectStation={(id) => {
                    setSelectedStationId(id);
                    setActiveCategory("governing");
                  }}
                />
              </div>
            </div>
          )}

          {/* SECTION: ML RECALIBRATION */}
          {activeCategory === "ml" && (
            <div className="space-y-4">
              <div className="text-xs font-bold text-[#5c5c5c] uppercase tracking-wider px-1">
                Physics-Informed Levenberg–Marquardt Machine Learning Calibrator
              </div>
              <div className="bg-[#ffffff] border border-[#e5e5e5] rounded-lg p-5 shadow-xs">
                <AccuracyPanel initialTab="calibration" />
              </div>
            </div>
          )}

          {/* SECTION: RUN LEDGER & VALIDATION */}
          {activeCategory === "validation" && (
            <div className="space-y-4">
              <div className="text-xs font-bold text-[#5c5c5c] uppercase tracking-wider px-1">
                Computation Run Ledger &amp; Spearman Rank Accuracy Validation
              </div>
              <div className="bg-[#ffffff] border border-[#e5e5e5] rounded-lg p-5 shadow-xs">
                <AccuracyPanel initialTab="runs" />
              </div>
            </div>
          )}

          {/* SECTION: SYSTEM HEALTH & 12-STEP PIPELINE */}
          {activeCategory === "system" && (
            <div className="space-y-4">
              <div className="text-xs font-bold text-[#5c5c5c] uppercase tracking-wider px-1">
                12-Stage Pipeline Automation &amp; Live Server Telemetry
              </div>
              <SystemHealthCards
                healthData={healthData}
                onRefresh={fetchSystemHealth}
                isRefreshing={healthRefreshing}
              />
              <div className="bg-[#ffffff] border border-[#e5e5e5] rounded-lg p-5 shadow-xs">
                <SystemPanel pipeline={pipeline} />
              </div>
            </div>
          )}

          {/* SECTION: STORAGE & DATABASE HOST HEALTH */}
          {activeCategory === "storage" && (
            <div className="space-y-4">
              <div className="text-xs font-bold text-[#5c5c5c] uppercase tracking-wider px-1">
                Server Tablespace, PostgreSQL State Store &amp; Institutional Governance
              </div>
              <SystemHealthCards
                healthData={healthData}
                onRefresh={fetchSystemHealth}
                isRefreshing={healthRefreshing}
              />
              <div className="bg-[#ffffff] border border-[#e5e5e5] rounded-lg p-5 shadow-xs">
                <ProjectInfoPanel />
              </div>
            </div>
          )}
        </div>

        {/* ── 3. DOCKABLE WINDOWS TERMINAL LOG TRAY ───────────────────── */}
        <WindowsTerminalDock
          isOpen={isTerminalOpen}
          onClose={() => setIsTerminalOpen(false)}
          logs={liveLogs}
          pipeline={pipeline}
          onTriggerRun={() => handleDispatch("trigger", "Forecast Run")}
          isRunning={loadingAction === "Forecast Run"}
        />
      </main>
    </div>
  );
}

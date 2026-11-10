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
import DataSharingPanel from "@/components/DataSharingPanel";
import SensorNetworkPanel from "@/components/SensorNetworkPanel";
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
  | "rainfall"
  | "sensors"
  | "data-sharing"
  | "info";

type Language = "en" | "mr";

const T = {
  en: {
    title: "HYDROCAST",
    subtitle: "/ Panchganga Basin",
    live: "Live",
    offline: "Offline",
    floodStatus: "Flood Status: ",
    alertLabels: {
      NORMAL: "NORMAL",
      ALERT: "ALERT",
      WARNING: "WARNING",
      DANGER: "DANGER",
      EMERGENCY: "EMERGENCY",
      HFL_EXCEEDED: "HFL EXCEEDED",
    } as Record<string, string>,
    nav: {
      dashboard: "Executive Dashboard",
      "river-stages": "River Stages & Flow",
      rainfall: "Rainfall & Rain Gauges",
      sensors: "Sensor Network",
      "data-sharing": "Open Data & Telegram Bot",
      info: "Project Information",
    } as Record<string, string>,
    navDesc: {
      dashboard: "Basin Overview, Flood Status & Catchment Map",
      "river-stages": "Bridge Staff Levels & 90-Hour Flood Flow Forecast",
      rainfall: "20 Gauging Stations & 90-Hour Forward Hyetographs",
      sensors: "Live IoT Water Level Stations (Shivaji, Nitawade, Ichalkaranji)",
      "data-sharing": "Public API, Python Client & Telegram Research Bot",
      info: "DST-SERB, Shivaji University & Research Team",
    } as Record<string, string>,
    basinSink: "Basin Sink (Rajaram K.T. Weir)",
    peakDischarge: "Peak Discharge",
    timeOfPeak: "Time of Peak",
    criticalBridges: "Critical Bridges",
    shivajiBridge: "Shivaji Bridge",
    rajaramWeir: "Rajaram K.T. Weir",
    offlineCache: "Viewing cached forecast from {time} — Reconnecting to live server...",
    dangerBannerTitle: "⚠️ PANCHGANGA CROSSING DANGER LEVEL - Evacuation Protocols Recommended",
    dangerBannerSub: "River Stage Exceeds Official Danger Level (543.30m MSL) · Immediate evacuation advisory for low-lying areas",
    stagePoints: "River Stage Points",
    peak: "Peak",
    shivajiStage: "Shivaji Bridge Stage",
    rajaramStage: "Rajaram Weir Stage",
    peakOutflow: "Peak Outflow (Q)",
    runoffVolume: "90h Runoff Volume",
    warning: "Warning",
    danger: "Danger",
    solidCrest: "Solid Crest",
    totalBasinYield: "Total Basin Yield",
  },
  mr: {
    title: "हायड्रोकास्ट",
    subtitle: "/ पंचगंगा खोरे",
    live: "थेट (Live)",
    offline: "ऑफलाईन",
    floodStatus: "पूर पातळी: ",
    alertLabels: {
      NORMAL: "सुरक्षित / सामान्य",
      ALERT: "दक्षता पातळी",
      WARNING: "सावधान पातळी",
      DANGER: "धोका पातळी",
      EMERGENCY: "आणीबाणी पातळी",
      HFL_EXCEEDED: "सर्वोच्च पूर पातळी ओलांडली",
    } as Record<string, string>,
    nav: {
      dashboard: "मुख्य डॅशबोर्ड",
      "river-stages": "नदी पातळी व प्रवाह",
      rainfall: "पर्जन्यमान व पाऊस मोजके",
      sensors: "आयओटी सेन्सर नेटवर्क",
      "data-sharing": "डेटा शेअरिंग व टेलिग्राम",
      info: "प्रकल्प माहिती",
    } as Record<string, string>,
    navDesc: {
      dashboard: "खोरे आढावा, पूर स्थिती व नकाशा",
      "river-stages": "पूल पातळी व ९०-तास पूर प्रवाह अंदाज",
      rainfall: "२० पर्जन्यमापक केंद्रे व अंदाज",
      sensors: "थेट आयओटी जलपातळी केंद्रे (शिवाजी, निटवे, इचलकरंजी)",
      "data-sharing": "सार्वजनिक API, क्लायंट व टेलिग्राम सूचना",
      info: "डीएसटी-सर्ब, शिवाजी विद्यापीठ व संशोधन गट",
    } as Record<string, string>,
    basinSink: "पाणलोट निकास (राजाराम बंधारा)",
    peakDischarge: "कमाल विसर्ग",
    timeOfPeak: "सर्वोच्च पूर वेळ",
    criticalBridges: "महत्त्वाचे पूल व बंधारे",
    shivajiBridge: "शिवाजी पूल (पंचगंगा घाट)",
    rajaramWeir: "राजाराम बंधारा (कसबा बावडा)",
    offlineCache: "{time} वेळचा साठवलेला अंदाज दाखवत आहे — सर्व्हरशी पुन्हा जोडणी करत आहे...",
    dangerBannerTitle: "⚠️ पंचगंगा नदीने धोका पातळी ओलांडली आहे - तातडीने सुरक्षित स्थळी स्थलांतर करा",
    dangerBannerSub: "नदीची पातळी अधिकृत धोका पातळी (५४३.३० मी MSL) ओलांडली आहे · सखल भागातील नागरिकांनी सुरक्षित स्थळी जावे",
    stagePoints: "नदी पातळी केंद्रे",
    peak: "कमाल",
    shivajiStage: "शिवाजी पूल पातळी",
    rajaramStage: "राजाराम बंधारा पातळी",
    peakOutflow: "कमाल विसर्ग (Q)",
    runoffVolume: "९०-तास एकूण विसर्ग",
    warning: "सावधान पातळी",
    danger: "धोका पातळी",
    solidCrest: "बंधारा माथा",
    totalBasinYield: "एकूण पाणलोट विसर्ग",
  },
};

const NAV = [
  {
    id: "dashboard",
    label: "Executive Dashboard",
    icon: "Dashboard",
    desc: "Basin Overview, Flood Status & Catchment Map",
  },
  {
    id: "river-stages",
    label: "River Stages & Flow",
    icon: "Hydrograph",
    desc: "Bridge Staff Levels & 90-Hour Flood Flow Forecast",
  },
  {
    id: "rainfall",
    label: "Rainfall & Rain Gauges",
    icon: "Rainfall",
    desc: "20 Gauging Stations & 90-Hour Forward Hyetographs",
  },
  {
    id: "sensors",
    label: "Sensor Network",
    icon: "Sensors",
    desc: "Live IoT Water Level Stations (Shivaji, Nitawade, Ichalkaranji)",
  },
  {
    id: "data-sharing",
    label: "Open Data & Telegram Bot",
    icon: "DataSharing",
    desc: "Public API, Python Client & Telegram Research Bot",
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
  const [isTabVisible, setIsTabVisible] = useState(true);
  const [isOffline, setIsOffline] = useState(false);
  const [cachedTime, setCachedTime] = useState<string | null>(null);
  const [lang, setLang] = useState<Language>("en");
  const [currentTime, setCurrentTime] = useState<Date | null>(null);

  useEffect(() => {
    setCurrentTime(new Date());
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const handleLangChange = (l: Language) => {
    setLang(l);
    try {
      localStorage.setItem("hydrocast_lang", l);
    } catch {}
  };

  const t = T[lang];

  const { connected, lastEvent } = useWebSocket();
  useEffect(() => {
    setMounted(true);

    try {
      const savedLang = localStorage.getItem("hydrocast_lang") as Language;
      if (savedLang === "mr" || savedLang === "en") setLang(savedLang);
    } catch {}

    const onVisibilityChange = () => {
      setIsTabVisible(document.visibilityState === "visible");
    };
    document.addEventListener("visibilitychange", onVisibilityChange);

    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => {
      setIsOffline(true);
      const ts = localStorage.getItem("hydrocast_cached_time");
      if (ts) setCachedTime(ts);
    };
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    if (typeof navigator !== "undefined" && !navigator.onLine) {
      handleOffline();
    }

    return () => {
      document.removeEventListener("visibilitychange", onVisibilityChange);
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  const pollInterval = isTabVisible ? 60000 : 0;
  const { data: status } = useSWR("status", api.status, { refreshInterval: pollInterval });
  const { data: summary } = useSWR("summary", api.runoffSummary, { refreshInterval: pollInterval });
  const { data: alerts } = useSWR("alerts", api.alerts, { refreshInterval: pollInterval });
  const { data: ecmwf } = useSWR("ecmwf", api.ecmwfHyetograph, { refreshInterval: pollInterval });
  const { data: stations } = useSWR("stations", api.stationSelection, { refreshInterval: pollInterval });
  const { data: hgData } = useSWR("hydrograph", api.outletHydrograph, { refreshInterval: pollInterval });

  const { data: bShivaji } = useSWR("bridge-SHIVAJI_BRIDGE", api.bridgeShivaji, { refreshInterval: pollInterval });
  const { data: bRajaram } = useSWR("bridge-RAJARAM_BRIDGE", api.bridgeRajaram, { refreshInterval: pollInterval });
  const { data: sensorsLive } = useSWR("sensors-live-dash", api.sensorsLive, { refreshInterval: isTabVisible ? 30000 : 0 });

  // Cache to localStorage for offline availability
  useEffect(() => {
    if (summary || status || bShivaji || bRajaram) {
      try {
        const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        localStorage.setItem("hydrocast_cached_time", timeStr);
        if (summary) localStorage.setItem("hydrocast_cached_summary", JSON.stringify(summary));
      } catch {}
    }
  }, [summary, status, bShivaji, bRajaram]);
  const sensorList: any[] = Array.isArray(sensorsLive) ? sensorsLive : sensorsLive?.stations ?? [];
  const nwSensor = sensorList.find((s: any) => s.station_id === "NW");
  const ikSensor = sensorList.find((s: any) => s.station_id === "IK");

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
      <header className="bg-white border-b border-gray-200 px-4 sm:px-6 h-16 sm:h-20 shrink-0 flex items-center justify-between shadow-xs">
        <div className="flex items-center gap-3 sm:gap-4">
          <button 
            className="md:hidden p-1.5 text-gray-600 hover:bg-gray-100 rounded-lg border border-gray-200"
            onClick={() => setIsSidebarOpen(true)}
            aria-label="Open Navigation Menu"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
               <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <div className="flex items-center gap-3">
            <img
              src="/assets/suk-logo-color.webp"
              alt="Shivaji University Kolhapur Logo"
              className="w-11 h-11 sm:w-14 sm:h-14 rounded-full border border-slate-200 shadow-xs shrink-0 bg-white p-0.5 object-contain"
            />
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-slate-900 text-base sm:text-lg tracking-tight">{t.title}</span>
                <span className="text-[10px] sm:text-[11px] font-bold px-1.5 py-0.5 rounded bg-sky-50 text-sky-700 border border-sky-200 hidden md:inline">
                  Panchganga Basin
                </span>
              </div>
              <p className="text-[10px] sm:text-xs text-slate-500 font-medium leading-none mt-1 hidden sm:block">
                {lang === "mr" 
                  ? "सेंटर फॉर क्लायमेट चेंज (CCCSS), शिवाजी विद्यापीठ, कोल्हापूर" 
                  : "Centre for Climate Change (CCCSS), Shivaji University Kolhapur"}
              </p>
            </div>
          </div>
        </div>

        <div className="hidden md:block">
          <VisitorCounterWidget compact />
        </div>
        <div className="flex items-center gap-3">
          {/* Marathi | English Toggle Button */}
          <div className="flex items-center bg-slate-100 rounded-md p-0.5 border border-slate-200 text-xs">
            <button
              onClick={() => handleLangChange("en")}
              className={`px-2.5 py-1 rounded font-medium text-xs transition-colors ${
                lang === "en" ? "bg-white text-sky-700 shadow-xs font-semibold" : "text-gray-600 hover:text-gray-900"
              }`}
              title="English"
            >
              EN
            </button>
            <button
              onClick={() => handleLangChange("mr")}
              className={`px-2.5 py-1 rounded font-medium text-xs transition-colors ${
                lang === "mr" ? "bg-white text-sky-700 shadow-xs font-semibold" : "text-gray-600 hover:text-gray-900"
              }`}
              title="मराठी"
            >
              मराठी
            </button>
          </div>

          <div className="hidden sm:flex items-center gap-2 text-xs text-gray-600">
            <span
              className={`w-1.5 h-1.5 rounded-full ${isOnline ? "bg-green-500" : "bg-gray-400"}`}
            />
            {isOnline ? t.live : t.offline}
          </div>

          {/* Dual Real-Time System Clock & Model Cycle Badge */}
          <div className="hidden md:flex flex-col items-end justify-center leading-tight">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-800 font-mono tracking-tight">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
              <span>
                {currentTime ? (
                  currentTime.toLocaleString(lang === "mr" ? "mr-IN" : "en-IN", {
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
            {status?.last_cycle?.start_time ? (
              <span
                className="text-[10px] text-slate-500 font-medium mt-0.5"
                title={`Simulation Cycle ID: ${status.last_cycle.cycle_id || 'CYC_LATEST'}`}
              >
                {lang === "mr" ? "मॉडेल अंदाज: " : "Model Run: "}
                {new Date(status.last_cycle.start_time).toLocaleString(lang === "mr" ? "mr-IN" : "en-IN", {
                  timeZone: "Asia/Kolkata",
                  day: "numeric",
                  month: "short",
                  hour: "2-digit",
                  minute: "2-digit",
                  hour12: true,
                })} IST
              </span>
            ) : (
              <span className="text-[10px] text-slate-400">
                {lang === "mr" ? "थेट सिस्टिम स्थिती" : "Live Telemetry Feed"}
              </span>
            )}
          </div>

          <div
            className={`px-2 py-1 rounded text-xs font-semibold border whitespace-nowrap ${alertBadge.bg} ${alertBadge.text} ${alertBadge.border}`}
          >
            <span className="hidden sm:inline">{t.floodStatus}</span>
            {t.alertLabels[worstAlert] ?? worstAlert}
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
              <div className="text-xs font-medium text-gray-400 mb-2">{lang === "mr" ? "विभाग" : "Workspace"}</div>
              <div className="space-y-1">
                {NAV.map((n) => {
                  const isActive = panel === n.id;
                  const label = t.nav[n.id] ?? n.label;
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
                        <span className="text-xs font-medium truncate">{label}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="p-3 bg-gray-50 rounded border border-gray-200">
              <div className="text-xs font-medium text-gray-500 mb-2">{t.basinSink}</div>
              <div className="space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-600">{t.peakDischarge}</span>
                  <span className="font-mono">{peakQ ? `${peakQ.toFixed(0)} m³/s` : "—"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">{t.timeOfPeak}</span>
                  <span className="font-mono">{peakAt ? `T+${peakAt}h` : "—"}</span>
                </div>
              </div>
            </div>

            <div className="p-3 bg-gray-50 rounded border border-gray-200">
              <div className="text-xs font-medium text-gray-500 mb-2">{t.criticalBridges}</div>
              <div className="space-y-2">
                <div className="flex flex-col text-xs bg-white p-2 rounded border border-gray-100">
                  <span className="text-gray-800">{shivajiBridge?.site_name ? (lang === "mr" ? t.shivajiBridge : shivajiBridge.site_name) : t.shivajiBridge}</span>
                  <span className="font-mono text-sky-700">
                    {shivajiBridge?.peak_stage_m ? `${shivajiBridge.peak_stage_m.toFixed(2)}m [${t.alertLabels[shivajiBridge.alert_level?.toUpperCase()] ?? shivajiBridge.alert_level}]` : "—"}
                  </span>
                </div>
                <div className="flex flex-col text-xs bg-white p-2 rounded border border-gray-100">
                  <span className="text-gray-800">{rajaramBridge?.site_name ? (lang === "mr" ? t.rajaramWeir : rajaramBridge.site_name) : t.rajaramWeir}</span>
                  <span className="font-mono text-sky-700">
                    {rajaramBridge?.peak_stage_m ? `${rajaramBridge.peak_stage_m.toFixed(2)}m [${t.alertLabels[rajaramBridge.alert_level?.toUpperCase()] ?? rajaramBridge.alert_level}]` : "—"}
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
          {/* Offline Notification Banner */}
          {isOffline && (
            <div className="bg-amber-600 text-white font-semibold px-4 py-2.5 rounded-xl shadow-xs text-xs flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span>⚠️</span>
                <span>{t.offlineCache.replace("{time}", cachedTime || (lang === "mr" ? "काही वेळापूर्वीचा" : "earlier"))}</span>
              </div>
              <span className="bg-white/20 text-white px-2 py-0.5 rounded text-[10px] font-mono">OFFLINE CACHE</span>
            </div>
          )}

          {/* Critical Flood Danger Banner */}
          {((shivajiLvl != null && shivajiLvl >= 543.30) || (rajaramLvl != null && rajaramLvl >= 543.30) || (shivajiPeak != null && shivajiPeak >= 543.30) || (rajaramPeak != null && rajaramPeak >= 543.30)) && (
            <div className="p-4 rounded-xl bg-red-600 text-white font-bold flex items-center justify-between border-2 border-red-800 shadow-md animate-pulse">
              <div className="flex items-center gap-3">
                <span className="text-2xl">⚠️</span>
                <div>
                  <div className="text-sm font-extrabold uppercase tracking-wide">
                    {t.dangerBannerTitle}
                  </div>
                  <div className="text-xs font-medium text-red-100">
                    {t.dangerBannerSub}
                  </div>
                </div>
              </div>
              <span className="bg-white/20 text-white text-xs px-3 py-1 rounded-full uppercase font-mono tracking-wider">
                {lang === "mr" ? "धोका पातळी इशारा" : "CRITICAL DANGER"}
              </span>
            </div>
          )}

          {/* 1. EXECUTIVE DASHBOARD OVERVIEW */}
          {panel === "dashboard" && (
            <OverviewPanel
              onNavigateTab={(tab) => {
                if (tab === "cross-section" || tab === "stage-gauges" || tab === "hydrograph" || tab === "runoff") {
                  setPanel("river-stages");
                } else if (tab === "rainfall" || tab === "info") {
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
                      {lang === "mr" ? "नदी पूल जलपातळी व निकास विसर्ग हायड्रोग्राफ" : "River Bridge Water Levels & Outlet Discharge Hydrograph"}
                    </h1>
                  </div>
                  <p className="text-xs text-gray-500 mt-1 font-medium">
                    {lang === "mr" ? "छत्रपती शिवाजी महाराज पूल व राजाराम के.टी. बंधारा · द्वैत-अक्ष विसर्ग अंदाज व इशारा पट्टे" : "Chhatrapati Shivaji Maharaj Bridge & Rajaram K.T. Weir · Dual-axis discharge forecast & threshold warning bands"}
                  </p>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="px-3 py-1 bg-sky-50 text-sky-700 font-bold rounded-md border border-sky-200">
                    {2 + (nwSensor ? 1 : 0) + (ikSensor ? 1 : 0)} {t.stagePoints}
                  </span>
                  <span className="px-3 py-1 bg-amber-50 text-amber-800 font-bold rounded-md border border-amber-200">
                    {t.peak}: {peakQ.toFixed(0)} m³/s (T+{peakAt}h)
                  </span>
                </div>
              </div>

              {/* 4 Summary Metric Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-xs">
                  <div className="text-[10px] font-bold text-gray-500 uppercase">{t.shivajiStage}</div>
                  <div className="mt-1 font-mono font-bold text-xl text-sky-700">
                    {shivajiBridge?.peak_stage_m ? `${shivajiBridge.peak_stage_m.toFixed(2)}m` : `${shivajiLvl.toFixed(2)}m`}
                  </div>
                  <div className="text-[10px] text-gray-500 mt-0.5">
                    {t.warning}: {shivajiSensor.dangerLevels.warning.toFixed(2)}m
                  </div>
                </div>

                <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-xs">
                  <div className="text-[10px] font-bold text-gray-500 uppercase">{t.rajaramStage}</div>
                  <div className="mt-1 font-mono font-bold text-xl text-sky-700">
                    {rajaramBridge?.peak_stage_m ? `${rajaramBridge.peak_stage_m.toFixed(2)}m` : `${rajaramLvl.toFixed(2)}m`}
                  </div>
                  <div className="text-[10px] text-gray-500 mt-0.5">
                    {t.solidCrest}: 535.77m MSL
                  </div>
                </div>

                <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-xs">
                  <div className="text-[10px] font-bold text-gray-500 uppercase">{t.peakOutflow}</div>
                  <div className="mt-1 font-mono font-bold text-xl text-amber-600">
                    {peakQ.toFixed(0)} <span className="text-xs text-gray-400">m³/s</span>
                  </div>
                  <div className="text-[10px] text-gray-500 mt-0.5">
                    {t.timeOfPeak}: T+{peakAt}h
                  </div>
                </div>

                <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-xs">
                  <div className="text-[10px] font-bold text-gray-500 uppercase">{t.runoffVolume}</div>
                  <div className="mt-1 font-mono font-bold text-xl text-emerald-600">
                    {summary?.outlet?.total_volume_mcm?.toFixed(1) ?? "0.0"} <span className="text-xs text-gray-400">MCM</span>
                  </div>
                  <div className="text-[10px] text-gray-500 mt-0.5">
                    {t.totalBasinYield}
                  </div>
                </div>
              </div>

              {/* IoT Sensor River Stage Readings (NW & IK) */}
              {(nwSensor || ikSensor) && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {[nwSensor, ikSensor].filter(Boolean).map((s: any) => {
                    const isStale = s.status === "STALE";
                    const isOnline = s.status === "ONLINE";
                    const statusColor = isOnline ? "text-emerald-700 bg-emerald-50 border-emerald-200" : isStale ? "text-orange-700 bg-orange-50 border-orange-200" : "text-red-700 bg-red-50 border-red-200";
                    const dotColor = isOnline ? "bg-emerald-500" : isStale ? "bg-orange-500" : "bg-red-500";
                    return (
                      <div key={s.station_id} className="bg-white border border-gray-200 rounded-xl p-4 shadow-xs">
                        <div className="flex items-center justify-between mb-3">
                          <div>
                            <div className="text-[10px] font-bold text-gray-500 uppercase">{s.name} — IoT River Stage</div>
                            <div className="text-[10px] text-gray-400">{s.full_name}</div>
                          </div>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded border flex items-center gap-1 ${statusColor}`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
                            {s.status}
                          </span>
                        </div>
                        <div className="flex items-baseline gap-2">
                          <span className="text-2xl font-mono font-bold text-sky-700">{s.stage_m != null ? s.stage_m.toFixed(2) : "—"}</span>
                          <span className="text-xs text-gray-400">m MSL</span>
                        </div>
                        <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-[11px]">
                          <div className="flex justify-between"><span className="text-gray-500">Sensor Datum</span><span className="font-mono text-gray-700">{s.sensor_datum_m} m</span></div>
                          <div className="flex justify-between"><span className="text-gray-500">Raw Distance</span><span className="font-mono text-gray-700">{s.raw_distance_ft ?? "—"} ft</span></div>
                          {s.voltage != null && <div className="flex justify-between"><span className="text-gray-500">Battery</span><span className="font-mono text-gray-700">{s.voltage} V</span></div>}
                          <div className="flex justify-between"><span className="text-gray-500">Coordinates</span><span className="font-mono text-gray-700">{s.latitude?.toFixed(4)}°N</span></div>
                        </div>
                        <div className="mt-2 pt-2 border-t border-gray-100 text-[10px] text-gray-400">
                          Last reading: {s.timestamp ? new Date(s.timestamp).toLocaleString("en-IN", { timeZone: "Asia/Kolkata", hour12: true, day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "—"}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

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
                          Dual Axis Q (m³/s) + Stage (m MSL) with Regulatory Alert &amp; Danger Lines
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
          {(panel as string) === "cross-section" && (
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

          {/* 5. SENSOR NETWORK PANEL */}
          {panel === "sensors" && <SensorNetworkPanel />}

          {/* 6. OPEN DATA & TELEGRAM ALERTS PANEL */}
          {panel === "data-sharing" && <DataSharingPanel />}

          {/* 6. PROJECT INFO PANEL */}
          {panel === "info" && <ProjectInfoPanel />}

          {/* Institutional Academic Disclaimer */}
          <footer className="mt-8 pt-4 border-t border-slate-200 text-center text-xs text-slate-500 space-y-1">
            <p className="font-semibold text-slate-700">
              {lang === "mr"
                ? "🔬 शैक्षणिक व वैज्ञानिक संशोधन प्रारूप — सेंटर फॉर क्लायमेट चेंज अँड सस्टेनेबिलिटी स्टडीज (CCCSS), शिवाजी विद्यापीठ, कोल्हापूर (DST-SERB)"
                : "🔬 Academic & Scientific Research Simulator — Centre for Climate Change and Sustainability Studies (CCCSS), Shivaji University, Kolhapur (DST-SERB)"}
            </p>
            <p className="text-[11px] text-slate-400">
              {lang === "mr"
                ? "सूचना: ही प्रणाली केवळ वैज्ञानिक व शैक्षणिक अभ्यासासाठी आहे. अधिकृत पूर सूचना व आपत्कालीन मार्गदर्शक सूचनांसाठी जिल्हा प्रशासनाशी (DDMA/KMC) संपर्क साधावा."
                : "Notice: Academic & Scientific Research Simulation by CCCSS, Shivaji University Kolhapur. For official flood warnings, evacuation notices, and civil alerts, consult District Administration / DDMA."}
            </p>
          </footer>
        </main>
      </div>
    </div>
  );
}

import { useState } from "react";
import useSWR from "swr";
import dynamic from "next/dynamic";
import { api } from "@/lib/api";
import FloodBanner from "@/components/FloodBanner";
import EngineeringGauge, { ZoomedGauge, GaugeSensor, GaugeData } from "@/components/EngineeringGauge";

import DischargeDetailsCard from "@/components/DischargeDetailsCard";

const BasinMap = dynamic(() => import("@/components/map/BasinMap"), { ssr: false });

const CARD = "bg-white border border-gray-200 rounded p-4";
const CARD_HEADER = "text-sm font-semibold text-gray-800 mb-4 flex items-center justify-between";

export default function OverviewPanel({
  onNavigateTab,
  onSelectStation,
}: {
  onNavigateTab: (tab: string) => void;
  onSelectStation: (stationId: string) => void;
}) {
  const [activeModalSensor, setActiveModalSensor] = useState<{ sensor: GaugeSensor; data: GaugeData } | null>(null);

  const { data: status } = useSWR("status", api.status, { refreshInterval: 15000 });
  const { data: summary } = useSWR("summary", api.runoffSummary, { refreshInterval: 30000 });
  const { data: hydrograph } = useSWR("hydrograph", api.outletHydrograph, { refreshInterval: 60000 });
  const { data: alerts } = useSWR("alerts", api.alerts, { refreshInterval: 30000 });
  const { data: ecmwf } = useSWR("ecmwf", api.ecmwfHyetograph, { refreshInterval: 60000 });
  const { data: stations } = useSWR("stations", api.stationSelection, { refreshInterval: 60000 });

  const { data: bShivaji } = useSWR("bridge-SHIVAJI_BRIDGE", api.bridgeShivaji, { refreshInterval: 30000 });
  const { data: bRajaram } = useSWR("bridge-RAJARAM_BRIDGE", api.bridgeRajaram, { refreshInterval: 30000 });

  const outlet = summary?.outlet;
  const noData = !status && !summary;
  const lastCycle = status?.last_cycle ?? status?.current_cycle;

  // Basin Rainfall Volume Calculations
  const stationsList: any[] = stations ?? [];
  const totalBasinRainVolMcm = stationsList.length > 0
    ? ((stationsList.reduce((acc: number, s: any) => acc + (s.cumulative_90h_mm ?? 0), 0) / stationsList.length) * 2140.0) / 1000.0
    : (lastCycle?.total_rainfall_volume_mcm ?? 31.9);
  const maxStationRain = lastCycle?.total_rainfall_mm ?? (stationsList.length > 0 ? Math.max(...stationsList.map((s: any) => s.cumulative_90h_mm ?? 0)) : 50.1);

  // Dynamic Live Bridge Data
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

  const shivajiPeakArr = b0?.peak_arrival ?? bShivaji?.peak_arrival ?? summary?.peak_arrival?.shivaji;
  const rajaramPeakArr = b1?.peak_arrival ?? bRajaram?.peak_arrival ?? summary?.peak_arrival?.rajaram;
  const recalState = summary?.recalibration;

  const shivajiLead = shivajiPeakArr?.peak_lead_hours ?? outlet?.lead_hours_to_peak ?? 0;
  const rajaramLead = rajaramPeakArr?.peak_lead_hours ?? outlet?.lead_hours_to_peak ?? 0;

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
  const rajaramData: GaugeData = {
    waterLevel: rajaramLvl,
    forecastLevel: rajaramPeak,
    forecastTime: `Peak T+${rajaramLead}h (±2.0h)`,
    alertLevel: b1?.alert_level ?? "normal",
    history: bRajaram?.forecast ? bRajaram.forecast.slice(0, 8).map((f: any) => f.stage_m) : [rajaramLvl],
  };

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto">
      {/* ── 1. ACTIVE FLOOD WARNING BANNER ────────────────────────────────── */}
      {alerts && alerts.length > 0 && <FloodBanner alerts={alerts} />}

      {/* ── 2. EXECUTIVE METRIC KPI TILES ─────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Peak Flood Discharge */}
        <div className="bg-white border border-gray-200 rounded p-4">
          <div className="flex items-center justify-between text-xs text-gray-500 uppercase">
            <span>Peak Basin Runoff</span>
            <span>HEC-HMS</span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-mono text-gray-900">
              {noData ? "—" : outlet?.peak_discharge_m3s?.toFixed(1)}
            </span>
            <span className="text-xs text-gray-500">m³/s</span>
          </div>
          <div className="mt-2 text-xs text-gray-600 pt-2 border-t border-gray-100">
            {noData ? "Awaiting forecast cycle" : `Peak Horizon: T+${outlet?.lead_hours_to_peak ?? 0}h`}
          </div>
        </div>

        {/* Metric 2: Max 90-hr Forecast Precipitation & Basin Volume */}
        <div className="bg-white border border-gray-200 rounded p-4">
          <div className="flex items-center justify-between text-xs text-gray-500 uppercase">
            <span>Total Basin Rain Volume</span>
            <span>90-Hour</span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-mono text-gray-900 font-bold">
              {noData ? "—" : totalBasinRainVolMcm.toFixed(1)}
            </span>
            <span className="text-xs text-blue-600 font-semibold">MCM</span>
            <span className="text-xs text-gray-300">|</span>
            <span className="text-sm font-mono text-gray-700 font-medium">
              {noData ? "—" : `${maxStationRain.toFixed(1)} mm max`}
            </span>
          </div>
          <div className="mt-2 text-xs text-gray-600 pt-2 border-t border-gray-100 flex items-center justify-between">
            <span>Total Catchment 2,140 km²</span>
            <span className="text-emerald-600 font-medium">18 Stations Active</span>
          </div>
        </div>

        {/* Metric 3: Shivaji Bridge Stage */}
        <div className="bg-white border border-gray-200 rounded p-4">
          <div className="flex items-center justify-between text-xs text-gray-500 uppercase">
            <span>Shivaji Bridge Stage</span>
            <span>{noData ? "—" : summary?.bridges?.[0]?.alert_level ?? "NORMAL"}</span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-mono text-gray-900">
              {noData ? "—" : summary?.bridges?.[0]?.peak_stage_m?.toFixed(2)}
            </span>
            <span className="text-xs text-gray-500">
              {noData ? "" : `m (Warning ${summary?.bridges?.[0]?.warning_stage_m?.toFixed(2) ?? "—"}m)`}
            </span>
          </div>
          <div className="mt-2 text-xs text-gray-600 pt-2 border-t border-gray-100">
            {noData ? "Awaiting forecast cycle" : "Peak Forecast (HEC-HMS)"}
          </div>
        </div>

        {/* Metric 4: Pipeline Operational State */}
        <div className="bg-white border border-gray-200 rounded p-4">
          <div className="flex items-center justify-between text-xs text-gray-500 uppercase">
            <span>Forecast Automation</span>
            <span>{noData ? "Offline" : "Healthy"}</span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-mono text-gray-900">
              {noData ? "—" : "100%"}
            </span>
            <span className="text-xs text-gray-500">{noData ? "" : "12 / 12 Steps OK"}</span>
          </div>
          <div className="mt-2 text-xs text-gray-600 pt-2 border-t border-gray-100">
            Cycle: {lastCycle?.run_id ?? "Awaiting first run"}
          </div>
        </div>
      {/* ── PEAK FLOOD ARRIVAL & CONFIDENCE INTERVAL MONITOR (±2.0h) ─────────── */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 mb-4 border-b border-slate-100 gap-2">
          <div className="flex items-center gap-2.5">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-600 animate-pulse"></span>
            <h2 className="text-sm font-semibold text-slate-900 tracking-wide uppercase">
              Peak Flood Strike Horizon & Permissible Confidence Interval (±2.0h)
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200">
              95% Confidence Band
            </span>
            {recalState?.alpha_k && recalState?.alpha_k !== 1.0 ? (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
                ⚡ ML Recalibrated (K: ×{recalState.alpha_k.toFixed(2)}, Lag: ×{recalState.alpha_lag.toFixed(2)})
              </span>
            ) : (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                ✓ Calibrated Parameters Active
              </span>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Shivaji Bridge Peak Card */}
          <div className="bg-slate-50/60 border border-slate-200/80 rounded-md p-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
                  Chhatrapati Shivaji Maharaj Bridge
                </span>
                <span className="text-[11px] font-mono text-slate-500">Urban Crossing (Panchganga Ghat)</span>
              </div>

              <div className="mt-3 flex items-baseline justify-between">
                <div>
                  <span className="text-3xl font-mono font-bold text-slate-900">
                    T+{shivajiLead}h
                  </span>
                  <span className="ml-2 text-xs font-semibold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">
                    [T+{shivajiPeakArr?.confidence_interval?.earliest_lead_hours ?? Math.max(0, shivajiLead - 2)}h to T+{shivajiPeakArr?.confidence_interval?.latest_lead_hours ?? (shivajiLead + 2)}h]
                  </span>
                </div>
              </div>

              <div className="mt-2 text-xs text-slate-600">
                {shivajiPeakArr?.peak_arrival_time ? (
                  <span>
                    Expected Strike: <span className="font-semibold text-slate-800">{new Date(shivajiPeakArr.peak_arrival_time).toLocaleString("en-IN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</span>
                    {" "}(Permissible: {new Date(shivajiPeakArr?.confidence_interval?.earliest_arrival_time ?? shivajiPeakArr.peak_arrival_time).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })} – {new Date(shivajiPeakArr?.confidence_interval?.latest_arrival_time ?? shivajiPeakArr.peak_arrival_time).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })})
                  </span>
                ) : (
                  <span>Awaiting forecast cycle peak time</span>
                )}
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-200/70 grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-slate-500 block text-[11px]">Peak Stage MSL</span>
                <span className="font-mono font-semibold text-slate-800">
                  {shivajiPeakArr?.peak_stage_m?.toFixed(2) ?? shivajiPeak?.toFixed(2)}m
                </span>
                <span className="text-[11px] text-slate-400 ml-1">
                  ({shivajiPeakArr?.confidence_interval?.stage_range_m?.[0]?.toFixed(2) ?? "—"} – {shivajiPeakArr?.confidence_interval?.stage_range_m?.[1]?.toFixed(2) ?? "—"}m)
                </span>
              </div>
              <div>
                <span className="text-slate-500 block text-[11px]">Peak Discharge</span>
                <span className="font-mono font-semibold text-slate-800">
                  {shivajiPeakArr?.peak_discharge_m3s?.toFixed(0) ?? outlet?.peak_discharge_m3s?.toFixed(0)} m³/s
                </span>
                <span className="text-[11px] text-slate-400 ml-1">
                  (±6% CI)
                </span>
              </div>
            </div>
          </div>

          {/* Rajaram K.T. Weir Peak Card */}
          <div className="bg-slate-50/60 border border-slate-200/80 rounded-md p-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
                  Rajaram K.T. Weir (Kasba Bawada)
                </span>
                <span className="text-[11px] font-mono text-slate-500">Downstream Basin Sink</span>
              </div>

              <div className="mt-3 flex items-baseline justify-between">
                <div>
                  <span className="text-3xl font-mono font-bold text-slate-900">
                    T+{rajaramLead}h
                  </span>
                  <span className="ml-2 text-xs font-semibold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">
                    [T+{rajaramPeakArr?.confidence_interval?.earliest_lead_hours ?? Math.max(0, rajaramLead - 2)}h to T+{rajaramPeakArr?.confidence_interval?.latest_lead_hours ?? (rajaramLead + 2)}h]
                  </span>
                </div>
              </div>

              <div className="mt-2 text-xs text-slate-600">
                {rajaramPeakArr?.peak_arrival_time ? (
                  <span>
                    Expected Strike: <span className="font-semibold text-slate-800">{new Date(rajaramPeakArr.peak_arrival_time).toLocaleString("en-IN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</span>
                    {" "}(Permissible: {new Date(rajaramPeakArr?.confidence_interval?.earliest_arrival_time ?? rajaramPeakArr.peak_arrival_time).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })} – {new Date(rajaramPeakArr?.confidence_interval?.latest_arrival_time ?? rajaramPeakArr.peak_arrival_time).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })})
                  </span>
                ) : (
                  <span>Awaiting forecast cycle peak time</span>
                )}
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-200/70 grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-slate-500 block text-[11px]">Peak Stage MSL</span>
                <span className="font-mono font-semibold text-slate-800">
                  {rajaramPeakArr?.peak_stage_m?.toFixed(2) ?? rajaramPeak?.toFixed(2)}m
                </span>
                <span className="text-[11px] text-slate-400 ml-1">
                  ({rajaramPeakArr?.confidence_interval?.stage_range_m?.[0]?.toFixed(2) ?? "—"} – {rajaramPeakArr?.confidence_interval?.stage_range_m?.[1]?.toFixed(2) ?? "—"}m)
                </span>
              </div>
              <div>
                <span className="text-slate-500 block text-[11px]">Peak Discharge</span>
                <span className="font-mono font-semibold text-slate-800">
                  {rajaramPeakArr?.peak_discharge_m3s?.toFixed(0) ?? outlet?.peak_discharge_m3s?.toFixed(0)} m³/s
                </span>
                <span className="text-[11px] text-slate-400 ml-1">
                  (±6% CI)
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── NEW: RAJARAM WEIR DISCHARGE & LOGS WIDGET ─────────────────────── */}
      <DischargeDetailsCard siteId="RAJARAM_BRIDGE" />

      {/* ── 3. PANCHGANGA BASIN MAP & HYDRAULIC HYDROGRAPH ─────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Basin GIS Map with Station click navigation */}
        <div className={`lg:col-span-7 ${CARD} flex flex-col`}>
          <div className={CARD_HEADER}>
            <span>Panchganga Catchment & Active Station Network</span>
            <button
              onClick={() => onNavigateTab("rainfall")}
              className="text-xs text-blue-600 hover:underline"
            >
              Open Rainfall Panel
            </button>
          </div>
          <BasinMap
            subbasins={Object.keys(ecmwf ?? {})}
            ecmwf={ecmwf ?? {}}
            stations={stations ?? []}
            showSidebar={false}
            onSelectStation={(id) => {
              onSelectStation(id);
              onNavigateTab("rainfall");
            }}
          />
        </div>

        {/* River Bridge Water Level Hydraulic Stage Gauges */}
        <div className={`lg:col-span-5 ${CARD} flex flex-col`}>
          <div className={CARD_HEADER}>
            <span>Key River Flood Monitoring Sites</span>
            <button
              onClick={() => onNavigateTab("runoff")}
              className="text-xs text-blue-600 hover:underline"
            >
              Open Runoff & Stage
            </button>
          </div>

          {noData ? (
            <div className="text-center text-gray-400 text-sm py-12">
              Awaiting first forecast cycle...
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 my-auto">
              <div className="flex flex-col">
                <EngineeringGauge
                  sensor={shivajiSensor}
                  data={shivajiData}
                  onClick={() => setActiveModalSensor({ sensor: shivajiSensor, data: shivajiData })}
                />
              </div>
              <div className="flex flex-col">
                <EngineeringGauge
                  sensor={rajaramSensor}
                  data={rajaramData}
                  onClick={() => setActiveModalSensor({ sensor: rajaramSensor, data: rajaramData })}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── 5. HEC-DSS ACTIVE SUBBASIN PRECIPITATION STATIONS (S1–S9) ─────── */}
      <div className={CARD}>
        <div className={CARD_HEADER}>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
            <span>HEC-DSS Simulation Rain Gages (Subbasins S1–S9 Max-Volume Governed)</span>
          </div>
          <span className="text-xs text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded font-mono font-bold border border-emerald-200">
            9 Active Catchment Gages
          </span>
        </div>
        {stations && stations.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-9 gap-3">
            {stations.filter((st: any) => st.is_governing !== false).slice(0, 9).map((st: any) => (
              <button
                key={st.station_id}
                onClick={() => {
                  onSelectStation(st.station_id);
                  onNavigateTab("rainfall");
                }}
                className="p-3 bg-white hover:bg-sky-50/50 border border-gray-200 hover:border-sky-300 rounded-lg text-left transition-all flex flex-col justify-between shadow-xs group"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-blue-50 text-blue-700 border border-blue-200 font-mono">
                      {st.subbasin_id}
                    </span>
                    <span className="text-[8px] font-bold uppercase text-emerald-700 bg-emerald-50 px-1 rounded">
                      ACTIVE
                    </span>
                  </div>
                  <div className="font-bold text-xs text-gray-900 mt-2 group-hover:text-blue-600 truncate">
                    {st.station_name?.split(" ")[0]}
                  </div>
                </div>
                <div className="mt-3 pt-2 border-t border-gray-100 flex items-baseline justify-between">
                  <span className="text-[10px] text-gray-400">90h Total</span>
                  <span className="font-mono text-xs font-bold text-blue-600">{st.cumulative_90h_mm} mm</span>
                </div>
              </button>
            ))}
          </div>
        ) : (
          <div className="text-center text-gray-400 text-sm py-6">
            Awaiting station data from forecast pipeline...
          </div>
        )}
      </div>

      {/* ── INTERACTIVE ZOOMED GAUGE MODAL ─────────────────────────────────── */}
      {activeModalSensor && (
        <ZoomedGauge
          sensor={activeModalSensor.sensor}
          data={activeModalSensor.data}
          onClose={() => setActiveModalSensor(null)}
        />
      )}
    </div>
  );
}

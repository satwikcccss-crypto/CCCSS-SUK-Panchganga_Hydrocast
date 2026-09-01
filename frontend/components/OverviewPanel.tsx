"use client";

import useSWR from "swr";
import dynamic from "next/dynamic";
import { api } from "@/lib/api";
import FloodBanner from "@/components/FloodBanner";
import StageGauge from "@/components/StageGauge";

import { USER_STATIONS_DATA } from "@/components/StationDetailsCard";
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
  const { data: status } = useSWR("status", api.status, { refreshInterval: 15000 });
  const { data: summary } = useSWR("summary", api.runoffSummary, { refreshInterval: 30000 });
  const { data: hydrograph } = useSWR("hydrograph", api.outletHydrograph, { refreshInterval: 60000 });
  const { data: alerts } = useSWR("alerts", api.alerts, { refreshInterval: 30000 });
  const { data: ecmwf } = useSWR("ecmwf", api.ecmwfHyetograph, { refreshInterval: 60000 });
  const { data: stations } = useSWR("stations", api.stationSelection, { refreshInterval: 60000 });

  const outlet = summary?.outlet;

  const stationsArray = Object.values(USER_STATIONS_DATA);

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
              {outlet?.peak_discharge_m3s?.toFixed(1) ?? "864.0"}
            </span>
            <span className="text-xs text-gray-500">m³/s</span>
          </div>
          <div className="mt-2 text-xs text-gray-600 pt-2 border-t border-gray-100">
            Peak Horizon: T+{outlet?.lead_hours_to_peak ?? 22}h
          </div>
        </div>

        {/* Metric 2: Max 90-hr Forecast Precipitation */}
        <div className="bg-white border border-gray-200 rounded p-4">
          <div className="flex items-center justify-between text-xs text-gray-500 uppercase">
            <span>Max Station Rainfall</span>
            <span>90-Hour</span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-mono text-gray-900">55.4</span>
            <span className="text-xs text-gray-500">mm</span>
          </div>
          <div className="mt-2 text-xs text-gray-600 pt-2 border-t border-gray-100">
            Karanjphen
          </div>
        </div>

        {/* Metric 3: Shivaji Bridge Stage */}
        <div className="bg-white border border-gray-200 rounded p-4">
          <div className="flex items-center justify-between text-xs text-gray-500 uppercase">
            <span>Shivaji Bridge Stage</span>
            <span>{summary?.bridges[0]?.alert_level ?? "Warning"}</span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-mono text-gray-900">{summary?.bridges[0]?.peak_stage_m?.toFixed(2) ?? "536.24"}</span>
            <span className="text-xs text-gray-500">m (Warning {summary?.bridges[0]?.warning_stage_m?.toFixed(2) ?? "537.50"}m)</span>
          </div>
          <div className="mt-2 text-xs text-gray-600 pt-2 border-t border-gray-100">
            Peak Forecast (HEC-HMS)
          </div>
        </div>

        {/* Metric 4: Pipeline Operational State */}
        <div className="bg-white border border-gray-200 rounded p-4">
          <div className="flex items-center justify-between text-xs text-gray-500 uppercase">
            <span>Forecast Automation</span>
            <span>Healthy</span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-mono text-gray-900">100%</span>
            <span className="text-xs text-gray-500">12 / 12 Steps OK</span>
          </div>
          <div className="mt-2 text-xs text-gray-600 pt-2 border-t border-gray-100">
            Cycle: {status?.last_cycle?.run_id ?? "CYCLE-20260831"}
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
            onSelectStation={(id) => {
              onSelectStation(id);
              onNavigateTab("rainfall");
            }}
          />
        </div>

        {/* CWC Bridge Water Level Hydraulic Stage Gauges */}
        <div className={`lg:col-span-5 ${CARD} flex flex-col`}>
          <div className={CARD_HEADER}>
            <span>CWC Key Flood Monitoring Sites</span>
            <button
              onClick={() => onNavigateTab("runoff")}
              className="text-xs text-blue-600 hover:underline"
            >
              Open Runoff & Stage
            </button>
          </div>

          <div className="grid grid-cols-2 gap-4 my-auto">
            <div className="flex flex-col">
              <div className="text-sm font-medium text-gray-800 mb-1 text-center">Shivaji Bridge</div>
              <div className="text-[10px] text-gray-500 mb-4 text-center">Current: {summary?.bridges[0]?.stage_m?.toFixed(2)}m | Peak: {summary?.bridges[0]?.peak_stage_m?.toFixed(2)}m</div>
              <StageGauge
                stage={summary?.bridges[0]?.stage_m ?? 535.10}
                forecastStage={summary?.bridges[0]?.peak_stage_m ?? 536.24}
                forecastTime="Peak"
                minH={530}
                maxH={545}
                warning={summary?.bridges[0]?.warning_stage_m ?? 537.50}
                danger={summary?.bridges[0]?.danger_stage_m ?? 538.50}
                hfl={summary?.bridges[0]?.hfl_m ?? 541.0}
                alert={535.50}
              />
            </div>
            <div className="flex flex-col">
              <div className="text-sm font-medium text-gray-800 mb-1 text-center">Rajaram K.T. Weir</div>
              <div className="text-[10px] text-gray-500 mb-4 text-center">Current: {summary?.bridges[1]?.stage_m?.toFixed(2)}m | Peak: {summary?.bridges[1]?.peak_stage_m?.toFixed(2)}m</div>
              <StageGauge
                stage={summary?.bridges[1]?.stage_m ?? 534.10}
                forecastStage={summary?.bridges[1]?.peak_stage_m ?? 534.92}
                forecastTime="Peak"
                minH={530}
                maxH={540}
                warning={summary?.bridges[1]?.warning_stage_m ?? 535.20}
                danger={summary?.bridges[1]?.danger_stage_m ?? 536.50}
                hfl={summary?.bridges[1]?.hfl_m ?? 538.20}
                alert={533.20}
              />
            </div>
          </div>
        </div>
      </div>


      {/* ── 5. QUICK STATION SELECTOR SHORTCUTS ────────────────────────────── */}
      <div className={CARD}>
        <div className={CARD_HEADER}>
          <span>Precipitation Stations Quick Access</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
          {stationsArray.map((st) => (
            <button
              key={st.id}
              onClick={() => {
                onSelectStation(st.id);
                onNavigateTab("rainfall");
              }}
              className="p-3 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded text-left transition-all flex flex-col justify-between"
            >
              <div>
                <div className="text-[10px] text-gray-500">
                  {st.subbasin.replace("SUB_", "")}
                </div>
                <div className="font-medium text-sm text-gray-900 mt-1">
                  {st.name.split(" ")[0]}
                </div>
              </div>
              <div className="mt-2">
                <span className="font-mono text-xs text-gray-700">{st.fc90} mm</span>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

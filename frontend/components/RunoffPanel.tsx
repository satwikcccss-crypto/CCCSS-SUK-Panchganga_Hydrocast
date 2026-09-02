"use client";
// frontend/components/RunoffPanel.tsx

import useSWR from "swr";
import { api } from "@/lib/api";
import HydrographChart from "@/components/charts/HydrographChart";
import CrossSectionViewer from "@/components/CrossSectionViewer";

const CARD = "bg-white border border-gray-200 rounded-xl p-5 shadow-xs";
const CARD_HEADER = "text-sm font-semibold text-gray-800 mb-4 flex items-center justify-between";

function KpiCard({
  label,
  value,
  unit,
  subtext,
  color,
  badge,
}: {
  label: string;
  value: string | number;
  unit: string;
  subtext?: string;
  color?: string;
  badge?: string;
}) {
  return (
    <div className={CARD}>
      <div className="flex items-center justify-between text-xs font-bold text-gray-500 uppercase tracking-wider">
        <span>{label}</span>
        {badge && (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-sky-50 text-sky-700 border border-sky-200">
            {badge}
          </span>
        )}
      </div>
      <div className="mt-3 flex items-baseline">
        <span className="text-3xl font-extrabold font-mono-code" style={{ color: color || "#0F172A" }}>
          {value}
        </span>
        {unit && <span className="text-sm font-bold text-gray-500 ml-1.5">{unit}</span>}
      </div>
      {subtext && <div className="mt-2 text-xs text-gray-500 font-medium">{subtext}</div>}
    </div>
  );
}

export default function RunoffPanel({ summary }: { summary: any }) {
  const { data: hgData } = useSWR("hydrograph", api.outletHydrograph, { refreshInterval: 60000 });
  const { data: bShivaji } = useSWR("bridge-SHIVAJI_BRIDGE", api.bridgeShivaji, { refreshInterval: 60000 });
  const { data: bRajaram } = useSWR("bridge-RAJARAM_BRIDGE", api.bridgeRajaram, { refreshInterval: 60000 });

  const outlet = summary?.outlet ?? {};
  const peakQ = outlet.peak_discharge_m3s ?? 864;
  const peakAt = outlet.lead_hours_to_peak ?? 22;
  const totalVol = outlet.total_runoff_volume_m3 ?? 148500000;
  const alertLvl = (outlet.alert_level ?? "WARNING").toUpperCase();

  const chartData = (hgData ?? []).map((r: any, i: number) => ({
    hour: i,
    q: r.discharge_m3s ?? 0,
    stage: r.stage_m ?? 0,
  }));

  return (
    <div className="flex flex-col gap-5 max-w-7xl mx-auto">
      {/* Top Title Banner */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
            <h1 className="text-base font-bold text-gray-900">
              Hydrological Runoff Discharge &amp; Bridge Flood Stage Forecast
            </h1>
          </div>
          <p className="text-xs text-gray-500 mt-1 font-medium">
            HEC-HMS 4.13 Simulation · SCS-CN Loss Method · Muskingum Channel Routing · 2D Surveyed Hydraulic Rating
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-medium">
          <span className="px-3 py-1 bg-amber-50 text-amber-800 font-semibold rounded-md border border-amber-200">
            Outlet: J_Outlet
          </span>
          <span className="px-3 py-1 bg-sky-50 text-sky-700 font-semibold rounded-md border border-sky-200">
            Lead Time: T+0h → T+89h
          </span>
        </div>
      </div>

      {/* Key Hydrological KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <KpiCard
          label="Current Discharge"
          value={(chartData[0]?.q ?? 45).toFixed(0)}
          unit="m³/s"
          subtext="Baseflow + Surface Runoff"
          color="#0284C7"
        />
        <KpiCard
          label="Peak Discharge"
          value={peakQ.toFixed(0)}
          unit="m³/s"
          subtext="HEC-HMS Simulation Peak"
          color="#F59E0B"
          badge="High"
        />
        <KpiCard
          label="Time to Peak (Tp)"
          value={`T+${peakAt}`}
          unit="hrs"
          subtext="Hydrologic Lag Time"
          color="#8B5CF6"
        />
        <KpiCard
          label="90-hr Runoff Volume"
          value={(totalVol / 1e6).toFixed(1)}
          unit="Mm³"
          subtext="Cumulative Basin Outflow"
          color="#0369A1"
        />
        <KpiCard
          label="Basin Alert Status"
          value={alertLvl}
          unit=""
          subtext="Hydrological Criteria"
          color={alertLvl === "WARNING" ? "#D97706" : "#10B981"}
          badge="BASIN"
        />
      </div>

      {/* Main Outlet Hydrograph */}
      <div className={CARD}>
        <div className={CARD_HEADER}>
          <span className="flex items-center gap-1.5 font-semibold text-gray-800">
            <span>📈</span> Sink Node (J_Outlet) Discharge &amp; Flood Stage Hydrograph
          </span>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold text-sky-700 bg-sky-50 px-2 py-0.5 rounded border border-sky-200">
              Dual Axis: Q (m³/s) + Stage (m)
            </span>
          </div>
        </div>
        <div className="mt-2">
          <HydrographChart
            data={chartData}
            thresholds={{ watch: 450, warning: 750, emergency: 1000 }}
            showStage
            height={280}
          />
        </div>
      </div>

      {/* Unified Interactive 2D River Cross Section & Hydraulic Station Telemetry */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="text-xs font-bold text-gray-700 uppercase tracking-wider flex items-center gap-2">
            <span>🌊</span> Downstream River Bridge Gauges &amp; 2D Cross-Section Simulation
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
    </div>
  );
}

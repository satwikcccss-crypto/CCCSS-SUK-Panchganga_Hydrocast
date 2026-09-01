"use client";
// frontend/components/RunoffPanel.tsx

import useSWR from "swr";
import { api } from "@/lib/api";
import HydrographChart from "@/components/charts/HydrographChart";
import StageGauge from "@/components/StageGauge";

const CARD = "bg-white border border-slate-200/90 rounded-xl p-5 shadow-xs transition-shadow hover:shadow-md";
const CARD_HEADER = "text-xs font-bold tracking-wider text-slate-500 uppercase flex items-center justify-between mb-3";

const ALERT_BADGES: Record<string, { bg: string; text: string; border: string }> = {
  NORMAL: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  ALERT: { bg: "bg-yellow-50", text: "text-yellow-800", border: "border-yellow-200" },
  WARNING: { bg: "bg-amber-50", text: "text-amber-800", border: "border-amber-200" },
  DANGER: { bg: "bg-rose-50", text: "text-rose-700", border: "border-rose-200" },
  HFL_EXCEEDED: { bg: "bg-purple-50", text: "text-purple-700", border: "border-purple-200" },
};

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
      <div className="flex items-center justify-between text-xs font-bold text-slate-500 uppercase tracking-wider">
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
        {unit && <span className="text-sm font-bold text-slate-500 ml-1.5">{unit}</span>}
      </div>
      {subtext && <div className="mt-2 text-xs text-slate-500 font-medium">{subtext}</div>}
    </div>
  );
}

function BridgeCard({ siteId, summary }: { siteId: string; summary: any }) {
  const { data: bData } = useSWR(`bridge-${siteId}`, () => api.bridgeStage(siteId), { refreshInterval: 60000 });

  const site = bData?.site ?? {};
  const forecast = bData?.forecast ?? [];
  const curr = forecast[0] ?? {};
  const level = (curr.alert_level ?? "NORMAL").toUpperCase();
  const badgeStyle = ALERT_BADGES[level] ?? ALERT_BADGES.NORMAL;

  const stageData = forecast.map((f: any, i: number) => ({
    hour: i,
    q: f.discharge_m3s ?? 0,
    stage: f.stage_m ?? 0,
  }));

  const arrivalRow = forecast.find((f: any) => f.alert_level && f.alert_level !== "NORMAL");
  const arrivalStr = arrivalRow
    ? `T+${arrivalRow.lead_hours ?? "?"}h (${new Date(arrivalRow.forecast_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} UTC)`
    : "No threshold breach projected in 90h window";

  const isAlert = ["WARNING", "DANGER", "HFL_EXCEEDED"].includes(level);

  return (
    <div className={`${CARD} flex flex-col justify-between`}>
      <div>
        {/* Header */}
        <div className="flex justify-between items-start mb-4 pb-3 border-b border-slate-100">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
              <h3 className="text-sm font-extrabold text-slate-900">{site.site_name ?? siteId}</h3>
            </div>
            <div className="text-xs text-slate-500 mt-0.5 font-medium">
              River Gauge Station · {(site.latitude ?? 17.68).toFixed(4)}°N, {(site.longitude ?? 74.01).toFixed(4)}°E
            </div>
          </div>
          <span
            className={`px-3 py-1 text-xs font-bold uppercase rounded-md border tracking-wider ${badgeStyle.bg} ${badgeStyle.text} ${badgeStyle.border}`}
          >
            ● {level}
          </span>
        </div>

        {/* Inner layout: Gauge + Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-center">
          {/* SVG Gauge */}
          <div className="md:col-span-4 flex justify-center">
            <StageGauge
              stage={curr.stage_m ?? 4.2}
              alert={site.alert_stage_m ?? 3.5}
              warning={site.warning_stage_m ?? 5.5}
              danger={site.danger_stage_m ?? 6.8}
              hfl={site.hfl_m ?? 8.5}
            />
          </div>

          {/* Details & Hydrograph Chart */}
          <div className="md:col-span-8 flex flex-col gap-3">
            {/* Threshold matrix */}
            <div className="grid grid-cols-4 gap-2 text-center text-xs">
              <div className="p-2 bg-yellow-50/70 border border-yellow-200 rounded-lg">
                <div className="text-[10px] font-bold text-yellow-800 uppercase">Alert</div>
                <div className="font-extrabold text-yellow-900 font-mono-code">{site.alert_stage_m ?? 3.5}m</div>
              </div>
              <div className="p-2 bg-amber-50/70 border border-amber-200 rounded-lg">
                <div className="text-[10px] font-bold text-amber-800 uppercase">Warning</div>
                <div className="font-extrabold text-amber-900 font-mono-code">{site.warning_stage_m ?? 5.5}m</div>
              </div>
              <div className="p-2 bg-rose-50/70 border border-rose-200 rounded-lg">
                <div className="text-[10px] font-bold text-rose-800 uppercase">Danger</div>
                <div className="font-extrabold text-rose-900 font-mono-code">{site.danger_stage_m ?? 6.8}m</div>
              </div>
              <div className="p-2 bg-purple-50/70 border border-purple-200 rounded-lg">
                <div className="text-[10px] font-bold text-purple-800 uppercase">HFL</div>
                <div className="font-extrabold text-purple-900 font-mono-code">{site.hfl_m ?? 8.5}m</div>
              </div>
            </div>

            {/* Current Stats */}
            <div className="grid grid-cols-3 gap-2 bg-slate-50 p-2.5 rounded-lg border border-slate-200 text-xs">
              <div>
                <div className="text-[10px] text-slate-500 font-medium">Discharge Q</div>
                <div className="font-bold text-sky-700 font-mono-code">{(curr.discharge_m3s ?? 310).toFixed(0)} m³/s</div>
              </div>
              <div>
                <div className="text-[10px] text-slate-500 font-medium">Stage Height</div>
                <div className="font-bold text-slate-900 font-mono-code">{(curr.stage_m ?? 4.2).toFixed(2)} m</div>
              </div>
              <div>
                <div className="text-[10px] text-slate-500 font-medium">HFL Safety Margin</div>
                <div className="font-bold text-emerald-600 font-mono-code">
                  {((site.hfl_m ?? 8.5) - (curr.stage_m ?? 4.2)).toFixed(2)} m
                </div>
              </div>
            </div>

            {/* Stage mini-chart */}
            <div>
              <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                90-Hour Stage Time Series (Manning's Q→H)
              </div>
              <HydrographChart data={stageData} thresholds={{}} showStage height={105} />
            </div>
          </div>
        </div>
      </div>

      {/* Footer / Flood arrival */}
      <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
        <div className="text-slate-600 font-medium">
          <span className="font-bold text-slate-800">Threshold Timing: </span>
          <span className={isAlert ? "font-semibold text-amber-700 font-mono-code" : "text-slate-500 font-mono-code"}>
            {arrivalStr}
          </span>
        </div>
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
          Bridge Telemetry
        </span>
      </div>
    </div>
  );
}

export default function RunoffPanel({ summary }: { summary: any }) {
  const { data: hgData } = useSWR("hydrograph", api.outletHydrograph, { refreshInterval: 60000 });

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
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
            <h1 className="text-base font-extrabold tracking-tight text-slate-900">
              Hydrological Runoff Discharge &amp; Bridge Flood Stage Forecast
            </h1>
          </div>
          <p className="text-xs text-slate-500 mt-1 font-medium">
            HEC-HMS Engine · SCS-CN Loss Method · Muskingum Channel Routing · Manning's Hydraulic Rating · Flood Alert Stages
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
          <span className="flex items-center gap-1.5 font-bold text-slate-800">
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

      {/* Bridge Stations Flood Forecast */}
      <div>
        <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
          Downstream River Bridge Monitoring Stations
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <BridgeCard siteId="SHIVAJI_BRIDGE" summary={summary} />
          <BridgeCard siteId="RAJARAM_BRIDGE" summary={summary} />
        </div>
      </div>
    </div>
  );
}

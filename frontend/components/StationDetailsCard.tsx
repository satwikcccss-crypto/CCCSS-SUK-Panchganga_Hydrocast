"use client";
// frontend/components/StationDetailsCard.tsx
// All data sourced from the real pipeline API — no hardcoded rainfall values

import { useState, useMemo } from "react";
import { Bar, Line } from "react-chartjs-2";
import {
  Chart as ChartJS, CategoryScale, LinearScale,
  BarElement, PointElement, LineElement, Title, Tooltip, Legend, Filler,
} from "chart.js";
import useSWR from "swr";
import { api } from "@/lib/api";

ChartJS.register(
  CategoryScale, LinearScale, BarElement, PointElement,
  LineElement, Title, Tooltip, Legend, Filler
);

// Static metadata only (coordinates, names) — NO hardcoded rainfall fc90 values
export const STATION_METADATA: Record<string, {
  id: string; name: string; subbasin: string;
  lat: number; lon: number; elevation: string; is_primary?: boolean;
}> = {
  // S1 (Area: 86.213 km²)
  KARVEER:         { id: "KARVEER",         name: "Karveer (Primary)",    subbasin: "S1", lat: 16.706369,  lon: 74.2481772, elevation: "550m", is_primary: true },
  KARVIR:          { id: "KARVIR",          name: "Karveer (Primary)",    subbasin: "S1", lat: 16.706369,  lon: 74.2481772, elevation: "550m", is_primary: true },

  // S2 (Area: 153.77 km²)
  SANGARUL:        { id: "SANGARUL",        name: "Sangarul (Primary)",   subbasin: "S2", lat: 16.6841962, lon: 74.0931627, elevation: "572m", is_primary: true },
  BALINGA:         { id: "BALINGA",         name: "Balinga (Alt)",        subbasin: "S2", lat: 16.6878443, lon: 74.17031,   elevation: "560m", is_primary: false },
  KALE:            { id: "KALE",            name: "Kale (Alt)",           subbasin: "S2", lat: 16.7228087, lon: 74.0564499, elevation: "580m", is_primary: false },

  // S3 (Area: 261.32 km²)
  KOTOLI:          { id: "KOTOLI",          name: "Kotoli (Primary)",     subbasin: "S3", lat: 16.7820174, lon: 74.0518705, elevation: "585m", is_primary: true },
  BAJAR_BHOGAON:   { id: "BAJAR_BHOGAON",  name: "Bajar Bhogaon (Alt)",  subbasin: "S3", lat: 16.8086769, lon: 74.1107824, elevation: "590m", is_primary: false },
  PADAL:           { id: "PADAL",           name: "Padal (Alt)",          subbasin: "S3", lat: 16.7446006, lon: 74.115187,  elevation: "575m", is_primary: false },

  // S4 (Area: 262.00 km²)
  KARANJPHEN:      { id: "KARANJPHEN",      name: "Karanjphen (Primary)", subbasin: "S4", lat: 16.7850973, lon: 73.9036487, elevation: "640m", is_primary: true },

  // S5 (Area: 106.39 km²)
  PADASALI:        { id: "PADASALI",        name: "Padasali (Primary)",   subbasin: "S5", lat: 16.701934,  lon: 73.843584,  elevation: "620m", is_primary: true },
  SALWAN:          { id: "SALWAN",          name: "Salwan (Alt)",         subbasin: "S5", lat: 16.6712,    lon: 73.9735,    elevation: "595m", is_primary: false },

  // S6 (Area: 227.72 km²)
  GAGANBAWDA:      { id: "GAGANBAWDA",      name: "Gaganbawda (Primary)", subbasin: "S6", lat: 16.5469926, lon: 73.8346738, elevation: "680m", is_primary: true },

  // S7 (Area: 195.39 km²)
  GARIVADE:        { id: "GARIVADE",        name: "Garivade (Primary)",   subbasin: "S7", lat: 16.520366,  lon: 73.918419,  elevation: "610m", is_primary: true },

  // S8 (Area: 177.44 km²)
  BEED:            { id: "BEED",            name: "Beed (Primary)",       subbasin: "S8", lat: 16.647984,  lon: 74.1288964, elevation: "565m", is_primary: true },
  SHIROLI_DHUMALA: { id: "SHIROLI_DHUMALA", name: "Shiroli-Dhumala (Alt)",subbasin: "S8", lat: 16.6166768, lon: 74.1062828, elevation: "560m", is_primary: false },

  // S9 (Area: 366.97 km²)
  RADHANAGARI:     { id: "RADHANAGARI",     name: "Radhanagari (Primary)",subbasin: "S9", lat: 16.41021,   lon: 73.9971822, elevation: "615m", is_primary: true },
  HALADI:          { id: "HALADI",          name: "Haladi (Alt)",         subbasin: "S9", lat: 16.5932632, lon: 74.156292,  elevation: "555m", is_primary: false },
  RASHIWADE_BK:    { id: "RASHIWADE_BK",    name: "Rashiwade Bk. (Alt)",  subbasin: "S9", lat: 16.5475641, lon: 74.1019728, elevation: "570m", is_primary: false },
  AAVALI_BK:       { id: "AAVALI_BK",       name: "Aavali Bk. (Alt)",    subbasin: "S9", lat: 16.481009,  lon: 74.0549812, elevation: "585m", is_primary: false },
  KASABA_TARALE:   { id: "KASABA_TARALE",   name: "Kasaba Tarale (Alt)",  subbasin: "S9", lat: 16.4478876, lon: 74.021589,  elevation: "595m", is_primary: false },
  KASABA_WALAWE:   { id: "KASABA_WALAWE",   name: "Kasaba Walawe (Alt)",  subbasin: "S9", lat: 16.41021,   lon: 73.9971822, elevation: "615m", is_primary: false },
};

export default function StationDetailsCard({
  stationId,
  onSelectStation,
}: {
  stationId: string;
  onSelectStation: (id: string) => void;
}) {
  const [activeTab, setActiveTab] = useState<"forecast">("forecast");

  // Fetch the real forecast hyetograph from the pipeline API
  const { data: ecmwf } = useSWR("ecmwf", api.ecmwfHyetograph, { refreshInterval: 60000 });
  const { data: stations } = useSWR("stations", api.stationSelection, { refreshInterval: 60000 });
  const { data: gauges } = useSWR("gauges", api.gaugeHyetographs, { refreshInterval: 60000 });

  const meta = STATION_METADATA[stationId] || STATION_METADATA.KARANJPHEN;

  // Find this station's real cumulative rainfall from the pipeline
  const stationRow = (stations ?? []).find((s: any) =>
    s.station_id === stationId || s.station_name?.toLowerCase().includes(meta.name.split(" ")[0].toLowerCase())
  );
  const realCumulative = stationRow?.cumulative_90h_mm ?? null;

  // Get the real hyetograph for this station (from gauges dictionary or subbasin)
  const subbasinKey = meta.subbasin;
  const hyetograph = gauges?.[stationId] ?? gauges?.[meta.id] ?? ecmwf?.[subbasinKey] ?? [];

  const noData = hyetograph.length === 0;

  // Build chart from real API hyetograph
  const forecastChart = useMemo(() => {
    if (noData) return { labels: [], datasets: [] };

    const cumPoints: number[] = [];
    let cum = 0;
    hyetograph.forEach((p: any) => {
      cum += (p.mm_hr ?? 0);
      cumPoints.push(parseFloat(cum.toFixed(2)));
    });

    return {
      labels: hyetograph.map((p: any) => `+${p.hour}h`),
      datasets: [
        {
          type: "bar" as const,
          label: "Forecast Hourly Intensity (mm/hr)",
          data: hyetograph.map((p: any) => p.mm_hr),
          backgroundColor: "#0284C7",
          borderRadius: 2,
          yAxisID: "y",
        },
        {
          type: "line" as const,
          label: "90-hr Cumulative (mm)",
          data: cumPoints,
          borderColor: "#10B981",
          backgroundColor: "rgba(16, 185, 129, 0.08)",
          fill: true,
          tension: 0.3,
          borderWidth: 2,
          pointRadius: 0,
          yAxisID: "y2",
        },
      ],
    };
  }, [hyetograph, noData]);

  const maxHourly = useMemo(() => {
    if (noData) return { value: 0, hour: 0 };
    let maxVal = 0, maxHr = 0;
    hyetograph.forEach((p: any) => {
      if (p.mm_hr > maxVal) { maxVal = p.mm_hr; maxHr = p.hour; }
    });
    return { value: maxVal, hour: maxHr };
  }, [hyetograph, noData]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "top" as const,
        align: "end" as const,
        labels: { color: "#475569", boxWidth: 10, font: { size: 10, weight: "600" as const } },
      },
    },
    scales: {
      x: {
        ticks: { color: "#64748B", font: { size: 8.5 }, maxTicksLimit: 14 },
        grid: { display: false },
      },
      y: {
        position: "left" as const,
        ticks: { color: "#64748B", font: { size: 9 } },
        grid: { color: "#F1F5F9" },
        title: { display: true, text: "Rainfall (mm/hr)", color: "#64748B", font: { size: 9, weight: "600" as const } },
      },
      y2: {
        position: "right" as const,
        ticks: { color: "#10B981", font: { size: 9 } },
        grid: { drawOnChartArea: false },
        title: { display: true, text: "Cumulative (mm)", color: "#10B981", font: { size: 9, weight: "600" as const } },
      },
    },
  };

  if (noData) {
    return (
      <div className="bg-white border-2 border-gray-200 rounded-2xl p-6 text-center text-gray-400">
        <div className="text-lg font-semibold mb-2">Awaiting Rainfall Data</div>
        <div className="text-sm">Run the pipeline to generate station hyetographs for {meta.name}.</div>
      </div>
    );
  }

  return (
    <div className="bg-white border-2 border-sky-500/80 rounded-2xl p-6 shadow-md transition-all">
      {/* Top Station Selector Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-sky-600 text-white flex items-center justify-center font-black text-lg shadow-sm">
            📡
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-extrabold text-slate-900">{meta.name}</h2>
              <span className="px-2 py-0.5 rounded-md text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                ACTIVE TELEMETRY
              </span>
            </div>
            <p className="text-xs text-slate-500 font-medium mt-0.5">
              Subbasin: <b className="text-sky-700">{meta.subbasin}</b> · Coordinates:{" "}
              <span className="font-mono font-bold text-slate-700">{meta.lat.toFixed(4)}°N, {meta.lon.toFixed(4)}°E</span> · Elev:{" "}
              <span className="font-bold text-slate-700">{meta.elevation}</span>
            </p>
          </div>
        </div>

        {/* Station Switcher Dropdown */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider hidden sm:inline">
            Switch Station:
          </span>
          <select
            value={stationId}
            onChange={(e) => onSelectStation(e.target.value)}
            className="text-xs font-bold text-slate-800 bg-slate-50 border border-slate-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-sky-500 shadow-xs"
          >
            {Object.values(STATION_METADATA).map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* 3 KPI Badges — from real data */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3.5 my-5">
        {/* 90-hr Total Forecast */}
        <div className="p-4 bg-sky-50/70 border border-sky-200 rounded-xl">
          <div className="text-[11px] font-bold uppercase tracking-wider text-sky-900 flex items-center justify-between">
            <span>90-hr Forecast Total</span>
            <span className="text-xs">🌧</span>
          </div>
          <div className="mt-2 text-2xl font-extrabold font-mono text-sky-950">
            {realCumulative?.toFixed(1) ?? "—"} <span className="text-xs font-bold text-sky-700">mm</span>
          </div>
          <div className="mt-1 text-[11px] font-semibold text-sky-800">
            Open-Meteo v1 ECMWF IFS
          </div>
        </div>

        {/* Peak Hourly Rate */}
        <div className="p-4 bg-emerald-50/70 border border-emerald-200 rounded-xl">
          <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-900 flex items-center justify-between">
            <span>Peak Hourly Forecast</span>
            <span className="text-xs">⏱</span>
          </div>
          <div className="mt-2 text-2xl font-extrabold font-mono text-emerald-950">
            {maxHourly.value.toFixed(2)} <span className="text-xs font-bold text-emerald-700">mm/hr</span>
          </div>
          <div className="mt-1 text-[11px] font-semibold text-emerald-800">
            Arrival at T+{maxHourly.hour}h
          </div>
        </div>

        {/* Subbasin Assignment */}
        <div className="p-4 bg-purple-50/60 border border-purple-200 rounded-xl">
          <div className="text-[11px] font-bold uppercase tracking-wider text-purple-900 flex items-center justify-between">
            <span>Subbasin Assignment</span>
            <span className="text-xs">📍</span>
          </div>
          <div className="mt-2 text-2xl font-extrabold font-mono text-purple-950">
            {meta.subbasin}
          </div>
          <div className="mt-1 text-[11px] font-semibold text-purple-800">
            {stationRow?.method ?? "Pipeline"} · {stationRow?.candidate_count ?? "—"} candidates
          </div>
        </div>
      </div>

      {/* Chart Tab */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-2 mb-3">
        <div className="flex items-center gap-2">
          <button
            className="px-3.5 py-1.5 text-xs font-bold rounded-lg bg-sky-600 text-white shadow-xs"
          >
            🌧 90-hr Forecast Hyetograph
          </button>
        </div>
        <div className="hidden sm:flex items-center gap-2 text-[11px] font-bold text-slate-500">
          <span>Real Pipeline Data</span>
        </div>
      </div>

      {/* Chart Canvas */}
      <div style={{ height: 260 }} className="w-full mt-2">
        <Bar
          data={forecastChart as any}
          options={chartOptions as any}
        />
      </div>
    </div>
  );
}

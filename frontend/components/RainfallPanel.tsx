"use client";

import { useState } from "react";
import useSWR from "swr";
import dynamic from "next/dynamic";
import { api } from "@/lib/api";
import HyetographChart from "@/components/charts/HyetographChart";
import StationDetailsCard, { USER_STATIONS_DATA } from "@/components/StationDetailsCard";

// Leaflet must be loaded client-side only
const BasinMap = dynamic(() => import("@/components/map/BasinMap"), { ssr: false });

const CARD = "bg-white border border-gray-200 rounded p-4";
const CARD_HEADER = "text-sm font-semibold text-gray-800 mb-4 flex items-center justify-between";

export default function RainfallPanel() {
  const [selectedStationId, setSelectedStationId] = useState<string>("KARANJPHEN");

  const { data: ecmwf } = useSWR("ecmwf", api.ecmwfHyetograph, { refreshInterval: 60000 });
  const { data: stations } = useSWR("stations", api.stationSelection, { refreshInterval: 60000 });
  const { data: gauges } = useSWR("gauges", api.gaugeHyetographs, { refreshInterval: 60000 });

  const subbasins = Object.keys(ecmwf ?? {});
  const selRows = stations ?? [];
  const palette = ["#0284C7", "#7C3AED", "#059669", "#D97706", "#EF4444"];

  const stationList = Object.values(USER_STATIONS_DATA);

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto">
      {/* Top Banner / Subtitle */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-500" />
            <h1 className="text-base font-bold text-gray-900">
              Open-Meteo v1 Forecast &amp; Panchganga Basin Station Intelligence
            </h1>
          </div>
          <p className="text-xs text-gray-500 mt-1 font-medium">
            Open-Meteo Forecast v1 API · 90-Day Historical Observations · 90-Hour Forward Prediction Window · HEC-DSS Export
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-medium">
          <span className="px-3 py-1 bg-sky-50 text-sky-800 font-bold rounded-md border border-sky-200">
            Open-Meteo v1 API
          </span>
          <span className="px-3 py-1 bg-emerald-50 text-emerald-800 font-bold rounded-md border border-emerald-200">
            7 Active Raingauge Stations
          </span>
        </div>
      </div>

      {/* ── STATION SELECTION CHIPS / QUICK BAR ───────────────────────── */}
      <div className="bg-white border border-gray-200 rounded p-4 shadow-sm flex items-center gap-2 overflow-x-auto">
        <span className="text-xs font-bold text-gray-500 uppercase tracking-wider whitespace-nowrap pl-1">
          Select Station:
        </span>
        <div className="flex items-center gap-2">
          {stationList.map((st) => {
            const isSelected = selectedStationId === st.id;
            return (
              <button
                key={st.id}
                onClick={() => setSelectedStationId(st.id)}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-2 whitespace-nowrap ${
                  isSelected
                    ? "bg-sky-600 text-white shadow-xs scale-105"
                    : "bg-slate-50 text-slate-700 hover:bg-slate-100 border border-slate-200"
                }`}
              >
                <span className={`w-2 h-2 rounded-full ${isSelected ? "bg-white" : "bg-emerald-500"}`} />
                <span>{st.name.split(" ")[0]}</span>
                <span className={`font-mono-code text-[11px] ${isSelected ? "text-sky-100" : "text-sky-700"}`}>
                  {st.fc90}mm
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── UNIFIED STATION KPI & TIME SERIES WIDGET (90d Past + 90h Future) ── */}
      <StationDetailsCard
        stationId={selectedStationId}
        onSelectStation={(id) => setSelectedStationId(id)}
      />

      {/* ── GIS BASIN MAP & CATCHMENT HYETOGRAPH ─────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Interactive Basin Map */}
        <div className={`lg:col-span-6 ${CARD} flex flex-col`}>
          <div className={CARD_HEADER}>
            <span className="flex items-center gap-1.5 font-semibold text-gray-800">
              <span>🗺</span> Panchganga Catchment &amp; Raingauge Station Map
            </span>
            <span className="text-[11px] font-medium text-sky-700 bg-sky-50 px-2 py-0.5 rounded border border-sky-200">
              Click Station Marker to Inspect
            </span>
          </div>
          <BasinMap
            subbasins={subbasins}
            ecmwf={ecmwf ?? {}}
            stations={selRows}
            selectedStationId={selectedStationId}
            onSelectStation={(id) => setSelectedStationId(id)}
          />
        </div>

        {/* Catchment Areal Hyetograph */}
        <div className={`lg:col-span-6 ${CARD} flex flex-col`}>
          <div className={CARD_HEADER}>
            <span className="flex items-center gap-1.5 font-semibold text-gray-800">
              <span>📊</span> Subbasin Areal Hyetographs (Open-Meteo mm/hr)
            </span>
            <span className="text-[11px] font-medium text-gray-500">90-Hour Time Series</span>
          </div>
          <div className="mt-2">
            <HyetographChart
              datasets={subbasins.map((sub, i) => ({
                label: sub,
                data: (ecmwf?.[sub] ?? []).map((d: any) => ({ x: d.hour, y: d.mm_hr })),
                color: palette[i % palette.length],
              }))}
              height={335}
            />
          </div>
        </div>
      </div>

      {/* ── STATION SELECTION AUDIT TABLE ────────────────────────────────── */}
      <div className={CARD}>
        <div className={CARD_HEADER}>
          <span className="flex items-center gap-1.5 font-semibold text-gray-800">
            <span>⚡</span> Open-Meteo Precipitation Stations Summary
          </span>
          <span className="text-[11px] font-semibold text-gray-500">
            Click row to activate station analytics widget
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
                <th className="py-3 px-4">Station Name</th>
                <th className="py-3 px-4">Subbasin Reach</th>
                <th className="py-3 px-4">90-hr Forecast</th>
                <th className="py-3 px-4">Past 90d Logged</th>
                <th className="py-3 px-4">Latitude</th>
                <th className="py-3 px-4">Longitude</th>
                <th className="py-3 px-4">Elevation</th>
                <th className="py-3 px-4">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {stationList.map((r) => {
                const isSelected = selectedStationId === r.id;
                return (
                  <tr
                    key={r.id}
                    onClick={() => setSelectedStationId(r.id)}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? "bg-sky-50 font-bold text-sky-950"
                        : "hover:bg-slate-50/80"
                    }`}
                  >
                    <td className="py-3 px-4 font-semibold text-slate-900 flex items-center gap-2">
                      <span className={`w-2.5 h-2.5 rounded-full ${isSelected ? "bg-sky-600" : "bg-emerald-500"}`} />
                      {r.name}
                    </td>
                    <td className="py-3 px-4 font-mono-code text-slate-600 text-[11px]">{r.subbasin}</td>
                    <td className="py-3 px-4 font-bold text-sky-700 font-mono-code">
                      {r.fc90.toFixed(1)} mm
                    </td>
                    <td className="py-3 px-4 font-bold text-purple-700 font-mono-code">
                      {(r.fc90 * 28 + 240).toFixed(0)} mm
                    </td>
                    <td className="py-3 px-4 font-mono-code text-slate-600">{r.lat.toFixed(4)}°N</td>
                    <td className="py-3 px-4 font-mono-code text-slate-600">{r.lon.toFixed(4)}°E</td>
                    <td className="py-3 px-4 font-bold text-slate-700">{r.elevation}</td>
                    <td className="py-3 px-4">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedStationId(r.id);
                        }}
                        className={`px-2.5 py-1 rounded text-[10px] font-bold uppercase transition-all ${
                          isSelected
                            ? "bg-sky-600 text-white shadow-xs"
                            : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                        }`}
                      >
                        {isSelected ? "Active" : "Inspect"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

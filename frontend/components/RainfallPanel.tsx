"use client";

import { useState, useMemo } from "react";
import useSWR from "swr";
import dynamic from "next/dynamic";
import { api } from "@/lib/api";
import HyetographChart from "@/components/charts/HyetographChart";
import StationDetailsCard, { STATION_METADATA } from "@/components/StationDetailsCard";

// Leaflet must be loaded client-side only
const BasinMap = dynamic(() => import("@/components/map/BasinMap"), { ssr: false });

const CARD = "bg-white border border-gray-200 rounded-xl p-5 shadow-xs";
const CARD_HEADER = "text-sm font-semibold text-gray-800 mb-4 flex items-center justify-between";

export default function RainfallPanel() {
  const [selectedStationId, setSelectedStationId] = useState<string>("KARANJPHEN");
  const [subbasinFilter, setSubbasinFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const { data: ecmwf } = useSWR("ecmwf", api.ecmwfHyetograph, { refreshInterval: 60000 });
  const { data: stations } = useSWR("stations", api.stationSelection, { refreshInterval: 60000 });

  const subbasins = Object.keys(ecmwf ?? {});
  const palette = ["#0284C7", "#7C3AED", "#059669", "#D97706", "#EF4444", "#8B5CF6", "#EC4899", "#14B8A6", "#6366F1"];

  // Canonical 20 stations list enriched with live API data so gauges are ALWAYS displayed
  const allStations = useMemo(() => {
    const rawList = Object.values(STATION_METADATA);
    return rawList.map((meta) => {
      const live = (stations ?? []).find(
        (s: any) =>
          s.station_id?.toUpperCase() === meta.id.toUpperCase() ||
          s.station_name?.toUpperCase() === meta.id.toUpperCase()
      );
      return {
        id: meta.id,
        name: meta.name.replace(/ \((Primary|Alt)\)/, ""),
        subbasin: meta.subbasin,
        cumulative: live?.cumulative_90h_mm ?? 0.0,
        lat: live?.lat ?? meta.lat,
        lon: live?.lon ?? meta.lon,
        elevation: live?.elevation ?? meta.elevation,
        is_primary: meta.is_primary ?? false,
        is_governing: live?.is_governing ?? meta.is_primary ?? false,
        method: live?.method ?? (meta.is_primary ? "PRIMARY" : "ALTERNATE"),
      };
    });
  }, [stations]);

  // Filtered station list based on search and subbasin
  const filteredStations = useMemo(() => {
    return allStations.filter((st) => {
      const matchSearch =
        st.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        st.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        st.subbasin.toLowerCase().includes(searchQuery.toLowerCase());
      if (!matchSearch) return false;
      if (subbasinFilter !== "ALL" && st.subbasin !== subbasinFilter) return false;
      return true;
    });
  }, [allStations, searchQuery, subbasinFilter]);

  // Deduplicated subbasin list
  const subbasinList = ["ALL", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9"];

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto w-full">
      {/* ── TOP BANNER ─────────────────────────────────────────────────── */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-500" />
            <h1 className="text-base font-bold text-gray-900">
              Panchganga Rain Gauge Network &amp; Precipitation Hyetographs
            </h1>
          </div>
          <p className="text-xs text-gray-500 mt-1 font-medium">
            20 Gauging Stations across Subbasins S1–S9 · Open-Meteo High-Resolution 90-Hour Forward Window
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-medium">
          <span className="px-3 py-1 bg-emerald-50 text-emerald-800 font-bold rounded-md border border-emerald-200">
            {allStations.length} Gauging Stations Registered
          </span>
        </div>
      </div>

      {/* ── SEARCH & SUBBASIN QUICK FILTER BAR ────────────────────────── */}
      <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-xs flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs font-bold text-gray-500 uppercase tracking-wider mr-1">
            Subbasin:
          </span>
          {subbasinList.map((sb) => (
            <button
              key={sb}
              onClick={() => setSubbasinFilter(sb)}
              className={`px-2.5 py-1 rounded text-xs font-mono font-bold transition-all ${
                subbasinFilter === sb
                  ? "bg-sky-600 text-white shadow-xs"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {sb}
            </button>
          ))}
        </div>

        <div className="relative">
          <input
            type="text"
            placeholder="Search gauge or subbasin..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="text-xs px-3 py-1.5 rounded-lg border border-gray-300 focus:outline-none focus:border-sky-500 w-52"
          />
        </div>
      </div>

      {/* ── INTERACTIVE STATION CHIPS SELECTOR ───────────────────────── */}
      <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-xs">
        <div className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3 flex items-center justify-between">
          <span>Active Rain Gauges ({filteredStations.length} Stations)</span>
          <span className="text-[11px] text-gray-400 font-normal">Click any station to inspect hyetograph</span>
        </div>

        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          {filteredStations.map((st) => {
            const isSelected = selectedStationId === st.id;
            return (
              <button
                key={st.id}
                onClick={() => setSelectedStationId(st.id)}
                className={`px-3.5 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 shrink-0 border ${
                  isSelected
                    ? "bg-sky-600 text-white border-sky-600 shadow-xs"
                    : "bg-slate-50 text-slate-700 hover:bg-slate-100 border-slate-200"
                }`}
              >
                <span className={`w-2 h-2 rounded-full ${isSelected ? "bg-white" : "bg-emerald-500"}`} />
                <span className="truncate max-w-[120px]">{st.name}</span>
                <span className={`font-mono text-[10px] px-1.5 py-0.5 rounded ${
                  isSelected ? "bg-sky-700 text-sky-100" : "bg-gray-200 text-gray-700"
                }`}>
                  {st.subbasin}
                </span>
                <span className={`font-mono text-[11px] ${isSelected ? "text-sky-100" : "text-sky-700 font-bold"}`}>
                  {st.cumulative.toFixed(1)} mm
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── UNIFIED SELECTED STATION KPI & TIME SERIES WIDGET ─────────── */}
      <StationDetailsCard
        stationId={selectedStationId}
        onSelectStation={(id) => setSelectedStationId(id)}
      />

      {/* ── GIS BASIN MAP & CATCHMENT HYETOGRAPH ───────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Interactive Basin Map */}
        <div className={`lg:col-span-6 ${CARD} flex flex-col`}>
          <div className={CARD_HEADER}>
            <span className="flex items-center gap-1.5 font-semibold text-gray-800">
              <span>🗺</span> Panchganga Catchment &amp; Rain Gauge Locations
            </span>
            <span className="text-[11px] font-medium text-sky-700 bg-sky-50 px-2 py-0.5 rounded border border-sky-200">
              Interactive Map
            </span>
          </div>
          <BasinMap
            subbasins={subbasins}
            ecmwf={ecmwf ?? {}}
            stations={allStations}
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

      {/* ── 20-STATION COMPREHENSIVE DIRECTORY TABLE ───────────────────── */}
      <div className={CARD}>
        <div className={CARD_HEADER}>
          <span className="flex items-center gap-1.5 font-semibold text-gray-800">
            <span>⚡</span> Complete Rain Gauge Station Directory
          </span>
          <span className="text-[11px] font-semibold text-gray-500">
            Showing {filteredStations.length} of {allStations.length} registered stations
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
                <th className="py-3 px-4">Station Name</th>
                <th className="py-3 px-4">Subbasin</th>
                <th className="py-3 px-4">Elevation</th>
                <th className="py-3 px-4">Coordinates (Lat / Lon)</th>
                <th className="py-3 px-4">Role</th>
                <th className="py-3 px-4">90-hr Forecast</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {filteredStations.map((r) => {
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
                      <span>{r.name}</span>
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-sky-700 text-xs">
                      {r.subbasin}
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-700">{r.elevation}</td>
                    <td className="py-3 px-4 font-mono text-slate-500 text-[11px]">
                      {r.lat.toFixed(4)}°N, {r.lon.toFixed(4)}°E
                    </td>
                    <td className="py-3 px-4">
                      {r.is_primary ? (
                        <span className="inline-block px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-sky-100 text-sky-800">
                          Primary
                        </span>
                      ) : (
                        <span className="inline-block px-2 py-0.5 rounded text-[10px] font-mono text-gray-600 bg-gray-100">
                          Alternate
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 font-bold text-sky-700 font-mono text-xs">
                      {r.cumulative.toFixed(1)} mm
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedStationId(r.id);
                        }}
                        className={`px-3 py-1 rounded text-xs font-bold transition-all ${
                          isSelected
                            ? "bg-sky-600 text-white shadow-xs"
                            : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                        }`}
                      >
                        {isSelected ? "Selected" : "Inspect"}
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

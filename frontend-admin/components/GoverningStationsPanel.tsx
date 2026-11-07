"use client";

import React, { useState, useMemo } from "react";
import {
  CloudRain,
  Search,
  Zap,
  Layers,
  MapPin,
  ArrowRight,
  TrendingUp,
  Info,
  CheckCircle2,
  Mountain,
} from "lucide-react";

export interface StationData {
  station_id: string;
  station_name: string;
  subbasin_id: string;
  lat: number;
  lon: number;
  elevation: string;
  cumulative_90h_mm?: number;
  is_primary?: boolean;
  is_governing?: boolean;
  method?: string;
  data_source?: string;
  active_telemetry?: boolean;
}

// 20 Canonical Stations from docs/raingauge-network.md & backend/rainfall/station_selector.py
const CANONICAL_REGISTRY: StationData[] = [
  { station_id: "KARVEER", station_name: "Karveer", subbasin_id: "S1", elevation: "550m MSL", lat: 16.706369, lon: 74.2481772, is_primary: true, is_governing: true },
  { station_id: "SANGARUL", station_name: "Sangarul", subbasin_id: "S2", elevation: "572m MSL", lat: 16.6841962, lon: 74.0931627, is_primary: true, is_governing: true },
  { station_id: "BALINGA", station_name: "Balinga", subbasin_id: "S2", elevation: "560m MSL", lat: 16.6878443, lon: 74.17031, is_primary: false, is_governing: false },
  { station_id: "KALE", station_name: "Kale", subbasin_id: "S2", elevation: "580m MSL", lat: 16.7228087, lon: 74.0564499, is_primary: false, is_governing: false },
  { station_id: "KOTOLI", station_name: "Kotoli", subbasin_id: "S3", elevation: "585m MSL", lat: 16.7820174, lon: 74.0518705, is_primary: true, is_governing: true },
  { station_id: "BAJAR_BHOGAON", station_name: "Bajar Bhogaon", subbasin_id: "S3", elevation: "590m MSL", lat: 16.8086769, lon: 74.1107824, is_primary: false, is_governing: false },
  { station_id: "PADAL", station_name: "Padal", subbasin_id: "S3", elevation: "575m MSL", lat: 16.7446006, lon: 74.115187, is_primary: false, is_governing: false },
  { station_id: "KARANJPHEN", station_name: "Karanjphen", subbasin_id: "S4", elevation: "640m MSL", lat: 16.7850973, lon: 73.9036487, is_primary: true, is_governing: true },
  { station_id: "PADASALI", station_name: "Padasali", subbasin_id: "S5", elevation: "620m MSL", lat: 16.701934, lon: 73.843584, is_primary: true, is_governing: true },
  { station_id: "SALWAN", station_name: "Salwan", subbasin_id: "S5", elevation: "595m MSL", lat: 16.6712, lon: 73.9735, is_primary: false, is_governing: false },
  { station_id: "GAGANBAWDA", station_name: "Gaganbawda", subbasin_id: "S6", elevation: "680m MSL", lat: 16.5469926, lon: 73.8346738, is_primary: true, is_governing: true },
  { station_id: "GARIVADE", station_name: "Garivade", subbasin_id: "S7", elevation: "610m MSL", lat: 16.520366, lon: 73.918419, is_primary: true, is_governing: true },
  { station_id: "BEED", station_name: "Beed", subbasin_id: "S8", elevation: "565m MSL", lat: 16.647984, lon: 74.1288964, is_primary: true, is_governing: true },
  { station_id: "SHIROLI_DHUMALA", station_name: "Shiroli-Dhumala", subbasin_id: "S8", elevation: "560m MSL", lat: 16.6166768, lon: 74.1062828, is_primary: false, is_governing: false },
  { station_id: "RADHANAGARI", station_name: "Radhanagari", subbasin_id: "S9", elevation: "615m MSL", lat: 16.41021, lon: 73.9971822, is_primary: true, is_governing: true },
  { station_id: "HALADI", station_name: "Haladi", subbasin_id: "S9", elevation: "555m MSL", lat: 16.5932632, lon: 74.156292, is_primary: false, is_governing: false },
  { station_id: "RASHIWADE_BK", station_name: "Rashiwade Bk.", subbasin_id: "S9", elevation: "570m MSL", lat: 16.5475641, lon: 74.1019728, is_primary: false, is_governing: false },
  { station_id: "AAVALI_BK", station_name: "Aavali Bk.", subbasin_id: "S9", elevation: "585m MSL", lat: 16.481009, lon: 74.0549812, is_primary: false, is_governing: false },
  { station_id: "KASABA_TARALE", station_name: "Kasaba Tarale", subbasin_id: "S9", elevation: "595m MSL", lat: 16.4478876, lon: 74.021589, is_primary: false, is_governing: false },
  { station_id: "KASABA_WALAWE", station_name: "Kasaba Walawe", subbasin_id: "S9", elevation: "615m MSL", lat: 16.41021, lon: 73.9971822, is_primary: false, is_governing: false },
];

// Subbasin official delineations from docs/raingauge-network.md & Basin_1.basin
const SUBBASIN_DEFINITIONS = [
  { id: "S1", name: "Karveer Lower Basin", area: 86.213, primary: "KARVEER", destination: "Rajaram Bridge (Sink-1)", candidates: ["KARVEER"] },
  { id: "S2", name: "Sangarul Subbasin", area: 153.770, primary: "SANGARUL", destination: "Reach R1", candidates: ["SANGARUL", "BALINGA", "KALE"] },
  { id: "S3", name: "Kotoli Subbasin", area: 261.320, primary: "KOTOLI", destination: "Reach R1", candidates: ["KOTOLI", "BAJAR_BHOGAON", "PADAL"] },
  { id: "S4", name: "Karanjphen Highland", area: 262.000, primary: "KARANJPHEN", destination: "Reach R3", candidates: ["KARANJPHEN"] },
  { id: "S5", name: "Padasali Subbasin", area: 106.390, primary: "PADASALI", destination: "Reach R3", candidates: ["PADASALI", "SALWAN"] },
  { id: "S6", name: "Gaganbawda Ghat Crest", area: 227.720, primary: "GAGANBAWDA", destination: "Reach R5", candidates: ["GAGANBAWDA"] },
  { id: "S7", name: "Garivade Subbasin", area: 195.390, primary: "GARIVADE", destination: "Reach R5", candidates: ["GARIVADE"] },
  { id: "S8", name: "Beed Valley", area: 177.440, primary: "BEED", destination: "Reach R2", candidates: ["BEED", "SHIROLI_DHUMALA"] },
  { id: "S9", name: "Radhanagari Catchment", area: 366.970, primary: "RADHANAGARI", destination: "Reach R4", candidates: ["RADHANAGARI", "HALADI", "RASHIWADE_BK", "AAVALI_BK", "KASABA_TARALE", "KASABA_WALAWE"] },
];

export default function GoverningStationsPanel({
  stations = [],
  bShivaji,
  bRajaram,
  summary,
}: {
  stations?: StationData[];
  bShivaji?: any;
  bRajaram?: any;
  summary?: any;
}) {
  const [searchFilter, setSearchFilter] = useState("");
  const [subbasinFilter, setSubbasinFilter] = useState<string>("ALL");
  const [roleFilter, setRoleFilter] = useState<"ALL" | "GOVERNING" | "PRIMARY" | "ALTERNATE">("ALL");

  // Merge canonical registry with live API station data if available
  const mergedStations = useMemo(() => {
    return CANONICAL_REGISTRY.map((can) => {
      const live = stations.find((s) => s.station_id === can.station_id || s.station_name === can.station_name);
      return {
        ...can,
        cumulative_90h_mm: live?.cumulative_90h_mm ?? 0.0,
        is_governing: live?.is_governing ?? can.is_governing,
        data_source: live?.data_source ?? "ECMWF_IFS_0.1",
      };
    });
  }, [stations]);

  // Filtered stations for the directory
  const filteredStations = useMemo(() => {
    return mergedStations.filter((s) => {
      const matchSearch =
        s.station_name.toLowerCase().includes(searchFilter.toLowerCase()) ||
        s.station_id.toLowerCase().includes(searchFilter.toLowerCase()) ||
        s.subbasin_id.toLowerCase().includes(searchFilter.toLowerCase());

      if (!matchSearch) return false;
      if (subbasinFilter !== "ALL" && s.subbasin_id !== subbasinFilter) return false;
      if (roleFilter === "GOVERNING" && !s.is_governing) return false;
      if (roleFilter === "PRIMARY" && !s.is_primary) return false;
      if (roleFilter === "ALTERNATE" && s.is_primary) return false;
      return true;
    });
  }, [mergedStations, searchFilter, subbasinFilter, roleFilter]);

  const governingStations = useMemo(() => {
    return mergedStations.filter((s) => s.is_governing);
  }, [mergedStations]);

  return (
    <div className="space-y-6">
      {/* ── 1. WEST-TO-EAST OROGRAPHIC RAINFALL GRADIENT PROFILE ── */}
      <div className="bg-[#ffffff] border border-[#e5e5e5] rounded-lg p-5 shadow-xs">
        <div className="pb-3 border-b border-[#f0f0f0] flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold text-[#1b1b1b] flex items-center gap-2">
              <Mountain className="w-4 h-4 text-[#0067b8]" />
              <span>Panchganga Orographic Elevation &amp; Rainfall Gradient</span>
            </h2>
            <p className="text-xs text-[#5c5c5c] mt-0.5">
              Topographic cross-section from the Sahyadri Ghat crest (Western edge) down to Kolhapur valley plain (Eastern sink)
            </p>
          </div>
          <div className="text-xs font-mono text-[#5c5c5c] bg-[#fafafa] border border-[#e5e5e5] px-3 py-1 rounded">
            Total Gauged Catchment: <span className="font-bold text-[#1b1b1b]">1,837.213 km²</span>
          </div>
        </div>

        {/* Orographic Altitude Bands Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mt-4 text-xs">
          {/* Band 1: Sahyadri Crest */}
          <div className="p-3.5 rounded-lg border border-[#cce4f7] bg-[#f0f7fc]">
            <div className="text-[10px] font-mono font-bold text-[#0067b8] uppercase tracking-wider">
              ~680m – 700m MSL
            </div>
            <div className="font-bold text-sm text-[#1b1b1b] mt-1">Ghat Crest Escarpment</div>
            <div className="text-[11px] text-[#004e8c] font-semibold mt-1">Gaganbawda (680m MSL)</div>
            <p className="text-[11px] text-[#5c5c5c] mt-2">
              Extreme orographic precipitation zone (~5,000 mm/year). Direct headwater driver of Reach R5.
            </p>
          </div>

          {/* Band 2: Upper Mountain Slopes */}
          <div className="p-3.5 rounded-lg border border-[#e0e0e0] bg-[#fafafa]">
            <div className="text-[10px] font-mono font-bold text-[#5c5c5c] uppercase tracking-wider">
              ~615m – 640m MSL
            </div>
            <div className="font-bold text-sm text-[#1b1b1b] mt-1">Upper Catchment Highlands</div>
            <div className="text-[11px] text-[#1b1b1b] font-semibold mt-1">Karanjphen, Padasali, Radhanagari</div>
            <p className="text-[11px] text-[#5c5c5c] mt-2">
              Heavy monsoon rainfall generating rapid surface runoff into Kasari, Tulshi, and Bhogawati river branches.
            </p>
          </div>

          {/* Band 3: Mid-Catchment Valleys */}
          <div className="p-3.5 rounded-lg border border-[#e0e0e0] bg-[#fafafa]">
            <div className="text-[10px] font-mono font-bold text-[#5c5c5c] uppercase tracking-wider">
              ~565m – 610m MSL
            </div>
            <div className="font-bold text-sm text-[#1b1b1b] mt-1">Mid-Valley Reaches</div>
            <div className="text-[11px] text-[#1b1b1b] font-semibold mt-1">Garivade, Kotoli, Sangarul, Beed</div>
            <p className="text-[11px] text-[#5c5c5c] mt-2">
              Moderate monsoon rainfall across agricultural terrain. Tributaries merge into Reach R2 and R1.
            </p>
          </div>

          {/* Band 4: Valley Floor & Sink */}
          <div className="p-3.5 rounded-lg border border-[#e0e0e0] bg-[#fafafa]">
            <div className="text-[10px] font-mono font-bold text-[#5c5c5c] uppercase tracking-wider">
              ~550m MSL
            </div>
            <div className="font-bold text-sm text-[#1b1b1b] mt-1">Valley Floor &amp; Terminal Sink</div>
            <div className="text-[11px] text-[#1b1b1b] font-semibold mt-1">Karveer (Kolhapur Urban Plain)</div>
            <p className="text-[11px] text-[#5c5c5c] mt-2">
              Lowest rainfall zone in catchment. Drains directly into Rajaram Bridge (Sink-1) with zero channel routing delay.
            </p>
          </div>
        </div>
      </div>

      {/* ── 2. DYNAMIC GOVERNING GAUGE INTELLIGENCE (MAX_VOL CONSERVATISM) ── */}
      <div className="bg-[#ffffff] border border-[#e5e5e5] rounded-lg p-5 shadow-xs">
        <div className="pb-3 border-b border-[#f0f0f0]">
          <h2 className="text-sm font-bold text-[#1b1b1b] flex items-center gap-2">
            <Zap className="w-4 h-4 text-[#0067b8]" />
            <span>Subbasin Governing Station Intelligence (MAX_VOL Selection)</span>
          </h2>
          <p className="text-xs text-[#5c5c5c] mt-0.5">
            On every forecast cycle, HydroCast evaluates all candidate gauges in each subbasin and selects the maximum-volume gauge for conservative flood defense
          </p>
        </div>

        {/* Subbasin Governing Matrix Table */}
        <div className="overflow-x-auto mt-4">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-[#e5e5e5] text-[#5c5c5c] font-semibold bg-[#fafafa]">
                <th className="py-2.5 px-3">Subbasin ID &amp; Name</th>
                <th className="py-2.5 px-3">Area (km²)</th>
                <th className="py-2.5 px-3">Candidate Rain Gauges</th>
                <th className="py-2.5 px-3">Governing Station Selected</th>
                <th className="py-2.5 px-3">Selection Rule</th>
                <th className="py-2.5 px-3 text-right">Drainage Destination</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f0f0f0]">
              {SUBBASIN_DEFINITIONS.map((sb) => {
                const governingSt = mergedStations.find((s) => s.subbasin_id === sb.id && s.is_governing);
                const hasCompetition = sb.candidates.length > 1;

                return (
                  <tr key={sb.id} className="hover:bg-[#f7f7f7] transition-colors">
                    <td className="py-2.5 px-3">
                      <div className="font-bold text-[#1b1b1b] flex items-center gap-1.5">
                        <span className="font-mono text-[#0067b8]">{sb.id}</span>
                        <span>· {sb.name}</span>
                      </div>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[#5c5c5c]">
                      {sb.area.toFixed(3)} km²
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="flex flex-wrap gap-1">
                        {sb.candidates.map((c) => (
                          <span
                            key={c}
                            className={`px-1.5 py-0.5 rounded text-[10px] font-mono ${
                              c === governingSt?.station_id
                                ? "bg-[#e0eef9] text-[#0067b8] font-bold border border-[#b8daf5]"
                                : "bg-[#f0f0f0] text-[#5c5c5c]"
                            }`}
                          >
                            {c}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="py-2.5 px-3 font-bold text-[#0067b8] font-mono">
                      {governingSt?.station_name ?? sb.primary}
                    </td>
                    <td className="py-2.5 px-3">
                      {hasCompetition ? (
                        <span className="inline-block text-[10px] font-mono text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded">
                          MAX_VOL Dynamic Competition
                        </span>
                      ) : (
                        <span className="inline-block text-[10px] font-mono text-[#767676] bg-[#f5f5f5] px-2 py-0.5 rounded">
                          Single Primary Station
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono font-semibold text-[#1b1b1b]">
                      {sb.destination}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Special Hydrological Notice */}
        <div className="mt-4 p-3 bg-[#fdf9e8] border border-[#f3e3a2] rounded-md text-xs text-[#735300] flex items-start gap-2">
          <Info className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">Station Geographic Verification Note: </span>
            <span>
              <code className="font-mono text-[11px]">KASABA_WALAWE</code> and{" "}
              <code className="font-mono text-[11px]">RADHANAGARI</code> share identical physical coordinates (73.9971822°E, 16.41021°N) in subbasin S9. When both report identical rainfall, ties are broken deterministically by alphabetical priority.
            </span>
          </div>
        </div>
      </div>

      {/* ── 3. OPERATIONAL RAIN GAUGE DIRECTORY (20 Canonical Stations) ── */}
      <div className="bg-[#ffffff] border border-[#e5e5e5] rounded-lg p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#f0f0f0]">
          <div>
            <h2 className="text-sm font-bold text-[#1b1b1b] flex items-center gap-2">
              <CloudRain className="w-4 h-4 text-[#0067b8]" />
              <span>Catchment Rain Gauge Directory ({filteredStations.length} of {CANONICAL_REGISTRY.length} Registered Stations)</span>
            </h2>
            <p className="text-xs text-[#5c5c5c] mt-0.5">
              Official station registry with surveyed elevations, geographic coordinates, and subbasin assignments
            </p>
          </div>

          {/* Search Bar */}
          <div className="relative">
            <Search className="absolute left-2.5 top-2 w-3.5 h-3.5 text-[#767676]" />
            <input
              type="text"
              placeholder="Search station or subbasin..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="bg-[#ffffff] border border-[#d1d1d1] focus:border-[#0067b8] rounded-md pl-8 pr-3 py-1 text-xs text-[#1a1a1a] outline-none w-56"
            />
          </div>
        </div>

        {/* Subbasin Quick Filter Pills */}
        <div className="flex flex-wrap gap-1.5 py-3 border-b border-[#f0f0f0] text-xs">
          <span className="text-[#767676] self-center mr-1 text-[11px]">Subbasin:</span>
          {["ALL", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9"].map((sb) => (
            <button
              key={sb}
              onClick={() => setSubbasinFilter(sb)}
              className={`px-2.5 py-0.5 rounded text-[11px] font-mono transition ${
                subbasinFilter === sb
                  ? "bg-[#0067b8] text-white font-bold"
                  : "bg-[#f0f0f0] text-[#5c5c5c] hover:bg-[#e5e5e5]"
              }`}
            >
              {sb}
            </button>
          ))}

          <span className="text-[#767676] self-center ml-3 mr-1 text-[11px]">Role:</span>
          {(["ALL", "GOVERNING", "PRIMARY", "ALTERNATE"] as const).map((r) => (
            <button
              key={r}
              onClick={() => setRoleFilter(r)}
              className={`px-2 py-0.5 rounded text-[11px] font-medium transition ${
                roleFilter === r
                  ? "bg-[#1b1b1b] text-white font-bold"
                  : "bg-[#f0f0f0] text-[#5c5c5c] hover:bg-[#e5e5e5]"
              }`}
            >
              {r}
            </button>
          ))}
        </div>

        {/* Station Table */}
        <div className="overflow-x-auto mt-3">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-[#e5e5e5] text-[#5c5c5c] font-semibold bg-[#fafafa]">
                <th className="py-2.5 px-3">Station Name &amp; ID</th>
                <th className="py-2.5 px-3">Subbasin</th>
                <th className="py-2.5 px-3">Elevation</th>
                <th className="py-2.5 px-3">Coordinates (Lat / Lon)</th>
                <th className="py-2.5 px-3">Role &amp; Status</th>
                <th className="py-2.5 px-3">90h Forward Depth</th>
                <th className="py-2.5 px-3 text-right">Governing Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f0f0f0]">
              {filteredStations.map((st) => (
                <tr key={st.station_id} className="hover:bg-[#f7f7f7] transition-colors">
                  <td className="py-2 px-3">
                    <div className="font-bold text-[#1b1b1b]">{st.station_name}</div>
                    <div className="text-[10px] font-mono text-[#767676]">{st.station_id}</div>
                  </td>
                  <td className="py-2 px-3 font-mono font-semibold text-[#0067b8]">
                    {st.subbasin_id}
                  </td>
                  <td className="py-2 px-3 font-mono text-[#1b1b1b]">
                    {st.elevation}
                  </td>
                  <td className="py-2 px-3 font-mono text-[11px] text-[#5c5c5c]">
                    {st.lat.toFixed(4)}°N, {st.lon.toFixed(4)}°E
                  </td>
                  <td className="py-2 px-3">
                    {st.is_primary ? (
                      <span className="inline-block text-[10px] font-mono font-semibold text-[#0067b8] bg-[#e0eef9] px-2 py-0.5 rounded">
                        Primary Station
                      </span>
                    ) : (
                      <span className="inline-block text-[10px] font-mono text-[#5c5c5c] bg-[#f0f0f0] px-2 py-0.5 rounded">
                        Alternate Station
                      </span>
                    )}
                  </td>
                  <td className="py-2 px-3 font-mono font-bold text-[#1b1b1b]">
                    {st.cumulative_90h_mm != null ? `${st.cumulative_90h_mm.toFixed(1)} mm` : "0.0 mm"}
                  </td>
                  <td className="py-2 px-3 text-right">
                    {st.is_governing ? (
                      <span className="inline-block text-[10px] font-mono font-bold text-white bg-[#0067b8] px-2 py-0.5 rounded">
                        GOVERNING
                      </span>
                    ) : (
                      <span className="inline-block text-[10px] font-mono text-[#767676] bg-[#f5f5f5] px-2 py-0.5 rounded">
                        STANDBY
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

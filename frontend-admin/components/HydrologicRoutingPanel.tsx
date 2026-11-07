"use client";

import React, { useState } from "react";
import {
  Waves,
  ArrowRight,
  TrendingUp,
  Sliders,
  ChevronDown,
  ChevronRight,
  Info,
  Layers,
  MapPin,
  Compass,
  Play,
  RotateCcw,
  Sparkles,
  GitCommit,
  GitFork,
  CheckCircle2,
} from "lucide-react";

// Ground-truth HEC-HMS Basin Model Data from Basin_1.basin (1,837.21 km²)
export const SUBBASINS = [
  {
    id: "S6",
    name: "Gaganbawda Ghat Crest",
    area_km2: 227.72,
    cn: 61.78,
    lag_hr: 55.3,
    downstream: "Reach R5",
    downstreamId: "R5",
    governing_station: "Gaganbawda",
    elevation: "720m MSL",
    river_tributary: "Upper Kumbhi River",
  },
  {
    id: "S7",
    name: "Radhanagari Basin Tributary",
    area_km2: 195.39,
    cn: 61.28,
    lag_hr: 56.0,
    downstream: "Reach R5",
    downstreamId: "R5",
    governing_station: "Radhanagari",
    elevation: "605m MSL",
    river_tributary: "Bhogawati Headwater",
  },
  {
    id: "S9",
    name: "Kasaba Tarale Mountain Headwater",
    area_km2: 366.97,
    cn: 64.31,
    lag_hr: 86.7,
    downstream: "Reach R4",
    downstreamId: "R4",
    governing_station: "Kasaba Tarale",
    elevation: "590m MSL",
    river_tributary: "Tulshi River Valley",
  },
  {
    id: "S8",
    name: "Beed Mid-Catchment Valley",
    area_km2: 177.44,
    cn: 65.76,
    lag_hr: 56.5,
    downstream: "Reach R2",
    downstreamId: "R2",
    governing_station: "Beed",
    elevation: "565m MSL",
    river_tributary: "Bhogawati River Mid",
  },
  {
    id: "S4",
    name: "Karanjphen Highland Subbasin",
    area_km2: 262.00,
    cn: 61.89,
    lag_hr: 51.9,
    downstream: "Reach R3",
    downstreamId: "R3",
    governing_station: "Karanjphen",
    elevation: "640m MSL",
    river_tributary: "Kasari River Upper",
  },
  {
    id: "S5",
    name: "Bajar Bhogaon Basin",
    area_km2: 106.39,
    cn: 60.97,
    lag_hr: 35.3,
    downstream: "Reach R3",
    downstreamId: "R3",
    governing_station: "Bajar Bhogaon",
    elevation: "610m MSL",
    river_tributary: "Kasari River Lower",
  },
  {
    id: "S3",
    name: "Kotoli Upper Catchment",
    area_km2: 261.32,
    cn: 64.82,
    lag_hr: 66.6,
    downstream: "Reach R1",
    downstreamId: "R1",
    governing_station: "Kotoli",
    elevation: "585m MSL",
    river_tributary: "Dhamani River",
  },
  {
    id: "S2",
    name: "Sangarul-Balinga Lateral Basin",
    area_km2: 153.77,
    cn: 65.74,
    lag_hr: 52.6,
    downstream: "Reach R1",
    downstreamId: "R1",
    governing_station: "Sangarul",
    elevation: "572m MSL",
    river_tributary: "Panchganga Main Stem",
  },
  {
    id: "S1",
    name: "Karveer Lower Basin (Urban Kolhapur)",
    area_km2: 86.21,
    cn: 74.85,
    lag_hr: 35.8,
    downstream: "Rajaram Bridge (Sink-1)",
    downstreamId: "Sink-1",
    governing_station: "Karveer",
    elevation: "550m MSL",
    river_tributary: "Direct to Rajaram Weir",
  },
];

// Ground-truth HEC-HMS Reaches from Basin_1.basin (Routing directly to Rajaram Bridge Sink)
export const REACHES = [
  {
    id: "R5",
    name: "Reach R5 (Upper Confluence)",
    inflows: "Subbasins S6 + S7",
    downstream: "Reach R2",
    downstreamId: "R2",
    k_hr: 4.619,
    x_factor: 0.20,
    type: "Natural River Channel",
    desc: "Combines Gaganbawda and Radhanagari mountain headwaters",
  },
  {
    id: "R4",
    name: "Reach R4 (Tulshi Tributary)",
    inflows: "Subbasin S9",
    downstream: "Reach R2",
    downstreamId: "R2",
    k_hr: 1.224,
    x_factor: 0.20,
    type: "Mountain Tributary Channel",
    desc: "Fast mountain runoff from Kasaba Tarale valley",
  },
  {
    id: "R3",
    name: "Reach R3 (Kasari Trunk)",
    inflows: "Subbasins S4 + S5",
    downstream: "Reach R1 (Shivaji Confluence)",
    downstreamId: "R1",
    k_hr: 3.829,
    x_factor: 0.20,
    type: "Compound Valley Channel",
    desc: "Routes combined Karanjphen and Bajar Bhogaon yield",
  },
  {
    id: "R2",
    name: "Reach R2 (Bhogawati Trunk)",
    inflows: "Reaches R5 + R4 + Subbasin S8",
    downstream: "Reach R1 (Shivaji Confluence)",
    downstreamId: "R1",
    k_hr: 11.827,
    x_factor: 0.20,
    type: "Major Alluvial Channel",
    desc: "Main Bhogawati river arm carrying majority basin flood volume",
  },
  {
    id: "R1",
    name: "Reach R1 (Panchganga Main Stem)",
    inflows: "Reaches R2 + R3 + Lateral S3 + S2",
    downstream: "Rajaram Bridge (Sink-1)",
    downstreamId: "Sink-1",
    k_hr: 2.899,
    x_factor: 0.20,
    type: "Urban Panchganga Reach via Shivaji Bridge",
    desc: "Main Panchganga river corridor passing Shivaji Bridge staff gauge directly into Rajaram Bridge Weir",
  },
];

export default function HydrologicRoutingPanel({
  recalState,
  summary,
}: {
  recalState?: any;
  summary?: any;
}) {
  const [selectedItem, setSelectedItem] = useState<{ type: "subbasin" | "reach" | "sink"; id: string }>({
    type: "sink",
    id: "Sink-1",
  });
  const [isSimulating, setIsSimulating] = useState(false);

  const subbasinParams = recalState?.active_sub_models || recalState?.baseline_sub_models || {};
  const reachParams = recalState?.active_reaches || recalState?.baseline_reaches || {};

  const peakQ = summary?.outlet?.peak_discharge_m3s ?? 0;
  const totalVolMcm = summary?.outlet?.total_volume_mcm ?? 0;
  const leadHours = summary?.outlet?.lead_hours_to_peak ?? 0;

  const currentSelectedSubbasin = SUBBASINS.find((s) => s.id === selectedItem.id);
  const currentSelectedReach = REACHES.find((r) => r.id === selectedItem.id);

  return (
    <div className="space-y-6">
      {/* ── 1. INTERACTIVE HYDROLOGICAL NETWORK SCHEMATIC (FLOW TO RAJARAM BRIDGE) ── */}
      <div className="bg-[#ffffff] border border-[#e5e5e5] rounded-lg p-5 shadow-xs">
        <div className="pb-4 border-b border-[#f0f0f0] flex flex-col lg:flex-row lg:items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-bold text-[#1b1b1b] flex items-center gap-2">
              <Waves className="w-4 h-4 text-[#0067b8]" />
              <span>Panchganga Hydrological Network &amp; Channel Routing to Rajaram Bridge Sink</span>
            </h2>
            <p className="text-xs text-[#5c5c5c] mt-0.5">
              Topological water flow architecture from 9 subbasins through 5 routing reaches into terminal control gauge
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                setIsSimulating(true);
                setTimeout(() => setIsSimulating(false), 4000);
              }}
              className={`win-btn ${isSimulating ? "primary" : ""}`}
              title="Visualize pulse routing downstream through the network"
            >
              <Play className={`w-3.5 h-3.5 ${isSimulating ? "animate-spin text-white" : "text-[#0067b8]"}`} />
              <span>{isSimulating ? "Simulating Wave..." : "Simulate Flow Pulse"}</span>
            </button>
            <div className="text-xs font-mono font-bold text-[#0067b8] bg-[#f0f7fc] border border-[#d0e5f7] px-3 py-1 rounded">
              Terminal Sink: Rajaram Bridge (RJKT)
            </div>
          </div>
        </div>

        {/* ── INTERACTIVE VISUAL FLOW MAP (DAG) ─────────────────────────── */}
        <div className="my-6 p-6 rounded-lg bg-gradient-to-b from-[#f9fafb] to-[#f0f7fc] border border-[#e2e8f0] overflow-x-auto">
          <div className="min-w-[980px] space-y-8">
            {/* TIER 1: Western Mountain Headwaters (S6, S7, S9, S4, S5) */}
            <div>
              <div className="text-[10px] font-bold text-[#767676] uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <span>Tier 1: Western Ghats Headwater Subbasins (Catchment Inflow Genesis)</span>
              </div>
              <div className="grid grid-cols-5 gap-3">
                {[
                  { sub: SUBBASINS[0], color: "emerald", branch: "Bhogawati Arm" },
                  { sub: SUBBASINS[1], color: "emerald", branch: "Bhogawati Arm" },
                  { sub: SUBBASINS[2], color: "cyan", branch: "Tulshi Arm" },
                  { sub: SUBBASINS[4], color: "blue", branch: "Kasari Arm" },
                  { sub: SUBBASINS[5], color: "blue", branch: "Kasari Arm" },
                ].map(({ sub, color, branch }) => (
                  <button
                    key={sub.id}
                    onClick={() => setSelectedItem({ type: "subbasin", id: sub.id })}
                    className={`p-3 rounded-lg border text-left transition-all ${
                      selectedItem.id === sub.id
                        ? "bg-white border-[#0067b8] shadow-md ring-2 ring-[#0067b8]/20"
                        : "bg-white border-[#d2d2d2] hover:border-[#0067b8] shadow-2xs"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-xs text-[#0067b8] bg-[#e0eef9] px-2 py-0.5 rounded">
                        {sub.id}
                      </span>
                      <span className="text-[10px] text-[#767676] font-mono">{sub.area_km2.toFixed(0)} km²</span>
                    </div>
                    <div className="text-xs font-bold text-[#1b1b1b] mt-1.5 truncate">{sub.name}</div>
                    <div className="text-[10px] text-[#5c5c5c] mt-0.5">CN: {sub.cn.toFixed(1)} · Lag: {sub.lag_hr.toFixed(1)}h</div>
                    <div className="mt-2 text-[10px] text-[#0067b8] font-mono flex items-center gap-1 font-semibold">
                      <span>Drains to:</span>
                      <span className="font-bold">{sub.downstreamId}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* FLOW ARROWS TIER 1 -> TIER 2 */}
            <div className="flex justify-around text-center text-xs text-[#0067b8] font-bold">
              <div className="flex-1 flex justify-center items-center gap-1">
                <span>↓ (S6 + S7)</span>
                <span className={`text-base ${isSimulating ? "animate-bounce" : ""}`}>↓</span>
              </div>
              <div className="flex-1 flex justify-center items-center gap-1">
                <span>↓ (S9)</span>
                <span className={`text-base ${isSimulating ? "animate-bounce" : ""}`}>↓</span>
              </div>
              <div className="flex-1 flex justify-center items-center gap-1">
                <span>↓ (S4 + S5)</span>
                <span className={`text-base ${isSimulating ? "animate-bounce" : ""}`}>↓</span>
              </div>
            </div>

            {/* TIER 2: Intermediate Reaches & Mid-Valley (R5, R4, S8, R3) */}
            <div>
              <div className="text-[10px] font-bold text-[#767676] uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-blue-500" />
                <span>Tier 2: Intermediate Reaches &amp; Valley Inflow Junctions</span>
              </div>
              <div className="grid grid-cols-4 gap-4">
                {/* Reach R5 */}
                <button
                  onClick={() => setSelectedItem({ type: "reach", id: "R5" })}
                  className={`p-3.5 rounded-lg border text-left transition-all ${
                    selectedItem.id === "R5"
                      ? "bg-white border-[#0067b8] shadow-md ring-2 ring-[#0067b8]/20"
                      : "bg-white border-[#d2d2d2] hover:border-[#0067b8] shadow-2xs"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-xs text-white bg-[#0067b8] px-2 py-0.5 rounded">R5</span>
                    <span className="text-[10px] text-[#767676] font-mono">K: 4.62h</span>
                  </div>
                  <div className="text-xs font-bold text-[#1b1b1b] mt-1.5">Upper Confluence Reach</div>
                  <div className="text-[10px] text-[#5c5c5c] mt-0.5">Inflow: S6 + S7</div>
                  <div className="mt-2 text-[10px] text-[#0067b8] font-mono font-semibold">↓ Outflow to Reach R2</div>
                </button>

                {/* Reach R4 */}
                <button
                  onClick={() => setSelectedItem({ type: "reach", id: "R4" })}
                  className={`p-3.5 rounded-lg border text-left transition-all ${
                    selectedItem.id === "R4"
                      ? "bg-white border-[#0067b8] shadow-md ring-2 ring-[#0067b8]/20"
                      : "bg-white border-[#d2d2d2] hover:border-[#0067b8] shadow-2xs"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-xs text-white bg-[#0067b8] px-2 py-0.5 rounded">R4</span>
                    <span className="text-[10px] text-[#767676] font-mono">K: 1.22h</span>
                  </div>
                  <div className="text-xs font-bold text-[#1b1b1b] mt-1.5">Tulshi Valley Reach</div>
                  <div className="text-[10px] text-[#5c5c5c] mt-0.5">Inflow: S9 (Kasaba Tarale)</div>
                  <div className="mt-2 text-[10px] text-[#0067b8] font-mono font-semibold">↓ Outflow to Reach R2</div>
                </button>

                {/* Subbasin S8 (Beed) */}
                <button
                  onClick={() => setSelectedItem({ type: "subbasin", id: "S8" })}
                  className={`p-3.5 rounded-lg border text-left transition-all ${
                    selectedItem.id === "S8"
                      ? "bg-white border-[#0067b8] shadow-md ring-2 ring-[#0067b8]/20"
                      : "bg-white border-[#d2d2d2] hover:border-[#0067b8] shadow-2xs"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-xs text-[#0067b8] bg-[#e0eef9] px-2 py-0.5 rounded">S8</span>
                    <span className="text-[10px] text-[#767676] font-mono">177.4 km²</span>
                  </div>
                  <div className="text-xs font-bold text-[#1b1b1b] mt-1.5">Beed Mid-Valley</div>
                  <div className="text-[10px] text-[#5c5c5c] mt-0.5">CN: 65.8 · Lag: 56.5h</div>
                  <div className="mt-2 text-[10px] text-[#0067b8] font-mono font-semibold">↓ Drains directly to R2</div>
                </button>

                {/* Reach R3 (Kasari) */}
                <button
                  onClick={() => setSelectedItem({ type: "reach", id: "R3" })}
                  className={`p-3.5 rounded-lg border text-left transition-all ${
                    selectedItem.id === "R3"
                      ? "bg-white border-[#0067b8] shadow-md ring-2 ring-[#0067b8]/20"
                      : "bg-white border-[#d2d2d2] hover:border-[#0067b8] shadow-2xs"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-xs text-white bg-[#0067b8] px-2 py-0.5 rounded">R3</span>
                    <span className="text-[10px] text-[#767676] font-mono">K: 3.83h</span>
                  </div>
                  <div className="text-xs font-bold text-[#1b1b1b] mt-1.5">Kasari Trunk Reach</div>
                  <div className="text-[10px] text-[#5c5c5c] mt-0.5">Inflow: S4 + S5</div>
                  <div className="mt-2 text-[10px] text-[#0067b8] font-mono font-semibold">↓ Outflow to Reach R1</div>
                </button>
              </div>
            </div>

            {/* FLOW ARROWS TIER 2 -> TIER 3 */}
            <div className="flex justify-between items-center text-xs text-[#0067b8] font-bold px-12">
              <div className="flex items-center gap-1">
                <span>(R5 + R4 + S8) ───► Merges into Major Trunk Reach R2</span>
                <span className={`text-base ${isSimulating ? "animate-pulse" : ""}`}>↓</span>
              </div>
              <div className="flex items-center gap-1">
                <span>(R3) ───► Kasari Arm</span>
                <span className={`text-base ${isSimulating ? "animate-pulse" : ""}`}>↓</span>
              </div>
            </div>

            {/* TIER 3: Main Panchganga Trunk Reach R2 & R1 (Passes Shivaji Bridge) */}
            <div>
              <div className="text-[10px] font-bold text-[#767676] uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-indigo-500" />
                <span>Tier 3: Main Panchganga River Corridor &amp; Control Points</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Reach R2 */}
                <button
                  onClick={() => setSelectedItem({ type: "reach", id: "R2" })}
                  className={`p-4 rounded-lg border text-left transition-all ${
                    selectedItem.id === "R2"
                      ? "bg-white border-[#0067b8] shadow-md ring-2 ring-[#0067b8]/20"
                      : "bg-white border-[#d2d2d2] hover:border-[#0067b8] shadow-2xs"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-xs text-white bg-[#0067b8] px-2 py-0.5 rounded">R2</span>
                    <span className="text-xs text-[#0067b8] font-mono font-bold">K: 11.83h (Longest Reach)</span>
                  </div>
                  <div className="text-xs font-bold text-[#1b1b1b] mt-1.5">Bhogawati Major Trunk Reach</div>
                  <div className="text-[11px] text-[#5c5c5c] mt-1">Carries largest volume of water from southern subbasins</div>
                  <div className="mt-2 text-[10px] text-[#0067b8] font-mono font-semibold">↓ Discharges into R1</div>
                </button>

                {/* Lateral Contributors S3 & S2 */}
                <div className="p-4 rounded-lg border border-[#e5e5e5] bg-[#fafafa] flex flex-col justify-between">
                  <div>
                    <span className="text-[10px] font-bold uppercase text-[#767676]">Lateral Inflows to R1</span>
                    <div className="mt-1 flex items-center gap-2">
                      <button
                        onClick={() => setSelectedItem({ type: "subbasin", id: "S3" })}
                        className="px-2.5 py-1 bg-white border border-[#d2d2d2] rounded text-xs font-mono font-bold text-[#0067b8] hover:border-[#0067b8]"
                      >
                        S3 Kotoli (261 km²)
                      </button>
                      <button
                        onClick={() => setSelectedItem({ type: "subbasin", id: "S2" })}
                        className="px-2.5 py-1 bg-white border border-[#d2d2d2] rounded text-xs font-mono font-bold text-[#0067b8] hover:border-[#0067b8]"
                      >
                        S2 Sangarul (154 km²)
                      </button>
                    </div>
                  </div>
                  <div className="text-[10px] text-[#5c5c5c] mt-2">Drains laterally along the main channel reach R1</div>
                </div>

                {/* Reach R1 (Shivaji Bridge) */}
                <button
                  onClick={() => setSelectedItem({ type: "reach", id: "R1" })}
                  className={`p-4 rounded-lg border text-left transition-all ${
                    selectedItem.id === "R1"
                      ? "bg-white border-[#0067b8] shadow-md ring-2 ring-[#0067b8]/20"
                      : "bg-white border-[#d2d2d2] hover:border-[#0067b8] shadow-2xs"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-xs text-white bg-[#0067b8] px-2 py-0.5 rounded">R1</span>
                    <span className="text-xs text-[#0f7b0f] font-mono font-bold">K: 2.90h</span>
                  </div>
                  <div className="text-xs font-bold text-[#1b1b1b] mt-1.5 flex items-center gap-1.5">
                    <span>Panchganga Main Channel</span>
                    <span className="text-[10px] bg-amber-100 text-amber-800 font-bold px-1.5 py-0.5 rounded">
                      Shivaji Bridge Staff Gauge
                    </span>
                  </div>
                  <div className="text-[11px] text-[#5c5c5c] mt-1">Passes Shivaji Bridge Ghats and conveys total basin flow</div>
                  <div className="mt-2 text-[10px] text-[#0067b8] font-mono font-bold">
                    ↓ Flows directly into Terminal Sink-1 (Rajaram Bridge)
                  </div>
                </button>
              </div>
            </div>

            {/* FLOW ARROW TIER 3 -> TIER 4 (THE SINK) */}
            <div className="flex justify-center items-center text-xs text-[#0067b8] font-bold gap-3">
              <span>Combined Reaches R1 + Local Urban Subbasin S1</span>
              <span className={`text-xl ${isSimulating ? "animate-bounce" : ""}`}>↓↓↓</span>
              <span className="text-emerald-700">TERMINAL OUTLET SINK</span>
            </div>

            {/* TIER 4: TERMINAL SINK AT RAJARAM BRIDGE (SINK-1) */}
            <div className="p-5 rounded-xl border-2 border-[#0067b8] bg-[#f0f7fc] shadow-md flex flex-col md:flex-row md:items-center justify-between gap-5">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-[#0067b8] to-[#004e8c] flex items-center justify-center text-white shadow-sm shrink-0">
                  <Waves className="w-7 h-7" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold uppercase tracking-wider text-white bg-[#0067b8] px-2.5 py-0.5 rounded">
                      TERMINAL MODEL SINK
                    </span>
                    <span className="text-xs text-[#0f7b0f] font-mono font-bold">● SINK-1 OUTLET</span>
                  </div>
                  <h3 className="text-base font-bold text-[#1b1b1b] mt-1">
                    Rajaram Bridge &amp; K.T. Weir (Kasba Bawada)
                  </h3>
                  <p className="text-xs text-[#5c5c5c] mt-0.5">
                    Total cumulative Panchganga Basin drainage confluence point (Catchment: 1,837.21 km²)
                  </p>
                </div>
              </div>

              {/* Real Metrics at Rajaram Bridge Sink */}
              <div className="flex items-center gap-4 border-t md:border-t-0 pt-3 md:pt-0 border-[#d0e5f7] font-mono text-xs">
                <div className="bg-white p-3 rounded-lg border border-[#d0e5f7] text-center">
                  <div className="text-[10px] text-[#767676] uppercase">Terminal Peak Q</div>
                  <div className="text-lg font-bold text-[#0067b8] mt-0.5">
                    {peakQ > 0 ? `${peakQ.toFixed(0)} m³/s` : "Synced"}
                  </div>
                </div>
                <div className="bg-white p-3 rounded-lg border border-[#d0e5f7] text-center">
                  <div className="text-[10px] text-[#767676] uppercase">Lead Time to Peak</div>
                  <div className="text-lg font-bold text-[#9d5d00] mt-0.5">
                    {leadHours > 0 ? `T+${leadHours}h` : "T+0h"}
                  </div>
                </div>
                <div className="bg-white p-3 rounded-lg border border-[#d0e5f7] text-center">
                  <div className="text-[10px] text-[#767676] uppercase">90h Outflow Vol</div>
                  <div className="text-lg font-bold text-[#0f7b0f] mt-0.5">
                    {totalVolMcm.toFixed(1)} MCM
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── INSPECTION DETAIL CARD FOR SELECTED SUBBASIN / REACH ────────── */}
        <div className="p-4 rounded-lg bg-[#f9fafb] border border-[#e5e5e5] text-xs">
          <div className="font-bold text-[#1b1b1b] flex items-center justify-between mb-2">
            <span className="flex items-center gap-1.5 text-[#0067b8]">
              <Info className="w-4 h-4" />
              <span>Inspection Inspector: {selectedItem.type.toUpperCase()} [{selectedItem.id}]</span>
            </span>
            <span className="text-[11px] text-[#767676] font-mono">From Basin_1.basin configuration</span>
          </div>

          {currentSelectedSubbasin && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono mt-3">
              <div>
                <span className="text-[#767676]">Subbasin Name: </span>
                <span className="font-bold text-[#1b1b1b]">{currentSelectedSubbasin.name}</span>
              </div>
              <div>
                <span className="text-[#767676]">Catchment Area: </span>
                <span className="font-bold text-[#0067b8]">{currentSelectedSubbasin.area_km2.toFixed(2)} km²</span>
              </div>
              <div>
                <span className="text-[#767676]">SCS Curve Number: </span>
                <span className="font-bold text-[#1b1b1b]">{currentSelectedSubbasin.cn.toFixed(2)}</span>
              </div>
              <div>
                <span className="text-[#767676]">Unit Lag Time: </span>
                <span className="font-bold text-[#9d5d00]">{currentSelectedSubbasin.lag_hr.toFixed(1)} hrs</span>
              </div>
              <div>
                <span className="text-[#767676]">Governing Gauge: </span>
                <span className="font-bold text-emerald-700">{currentSelectedSubbasin.governing_station}</span>
              </div>
              <div>
                <span className="text-[#767676]">Elevation Datum: </span>
                <span className="font-bold text-[#1b1b1b]">{currentSelectedSubbasin.elevation}</span>
              </div>
              <div>
                <span className="text-[#767676]">River Tributary: </span>
                <span className="font-bold text-[#1b1b1b]">{currentSelectedSubbasin.river_tributary}</span>
              </div>
              <div>
                <span className="text-[#767676]">Downstream Target: </span>
                <span className="font-bold text-[#0067b8]">{currentSelectedSubbasin.downstream}</span>
              </div>
            </div>
          )}

          {currentSelectedReach && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono mt-3">
              <div>
                <span className="text-[#767676]">Reach Segment: </span>
                <span className="font-bold text-[#1b1b1b]">{currentSelectedReach.name}</span>
              </div>
              <div>
                <span className="text-[#767676]">Muskingum K (Travel): </span>
                <span className="font-bold text-[#0067b8]">{currentSelectedReach.k_hr.toFixed(3)} hrs</span>
              </div>
              <div>
                <span className="text-[#767676]">Attenuation X Factor: </span>
                <span className="font-bold text-[#1b1b1b]">{currentSelectedReach.x_factor.toFixed(2)}</span>
              </div>
              <div>
                <span className="text-[#767676]">Inflow Sources: </span>
                <span className="font-bold text-emerald-700">{currentSelectedReach.inflows}</span>
              </div>
              <div>
                <span className="text-[#767676]">Downstream Target: </span>
                <span className="font-bold text-[#0067b8]">{currentSelectedReach.downstream}</span>
              </div>
              <div>
                <span className="text-[#767676]">Routing Scheme: </span>
                <span className="font-bold text-[#1b1b1b]">{currentSelectedReach.type}</span>
              </div>
              <div className="col-span-2">
                <span className="text-[#767676]">Hydraulic Description: </span>
                <span className="font-semibold text-[#1b1b1b]">{currentSelectedReach.desc}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── 2. SUBBASIN-WISE CATCHMENT YIELD SPECIFICATION TABLE ─────────── */}
      <div className="bg-[#ffffff] border border-[#e5e5e5] rounded-lg p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-[#f0f0f0]">
          <div>
            <h2 className="text-sm font-bold text-[#1b1b1b] flex items-center gap-2">
              <Layers className="w-4 h-4 text-[#0067b8]" />
              <span>Subbasin-Wise Runoff &amp; SCS Loss Parameters (Basin 1)</span>
            </h2>
            <p className="text-xs text-[#5c5c5c] mt-0.5">
              Exact SCS Runoff parameters and routing destinations terminating at Rajaram Bridge
            </p>
          </div>
          <div className="text-xs font-mono font-bold text-[#0067b8] bg-[#f0f7fc] border border-[#d0e5f7] px-3 py-1 rounded">
            Total Basin Drainage: 1,837.21 km² · 100% Routed to Rajaram Bridge
          </div>
        </div>

        <div className="overflow-x-auto mt-4">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-[#e5e5e5] text-[#5c5c5c] font-semibold bg-[#fafafa]">
                <th className="py-2.5 px-3">Subbasin</th>
                <th className="py-2.5 px-3">Subbasin Name</th>
                <th className="py-2.5 px-3">Area (km²)</th>
                <th className="py-2.5 px-3">Curve Number</th>
                <th className="py-2.5 px-3">SCS Lag (hr)</th>
                <th className="py-2.5 px-3">Governing Station</th>
                <th className="py-2.5 px-3">Tributary River</th>
                <th className="py-2.5 px-3 text-right">Downstream Destination</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f0f0f0]">
              {SUBBASINS.map((sub) => {
                const isSelected = selectedItem.id === sub.id;
                const isDirectSink = sub.id === "S1";

                return (
                  <tr
                    key={sub.id}
                    onClick={() => setSelectedItem({ type: "subbasin", id: sub.id })}
                    className={`cursor-pointer transition-colors ${
                      isSelected ? "bg-[#f0f7fc] font-semibold text-[#0067b8]" : "hover:bg-[#f7f7f7] text-[#1b1b1b]"
                    }`}
                  >
                    <td className="py-2.5 px-3 font-mono font-bold">{sub.id}</td>
                    <td className="py-2.5 px-3">{sub.name}</td>
                    <td className="py-2.5 px-3 font-mono">{sub.area_km2.toFixed(2)}</td>
                    <td className="py-2.5 px-3 font-mono">{sub.cn.toFixed(2)}</td>
                    <td className="py-2.5 px-3 font-mono">{sub.lag_hr.toFixed(1)}h</td>
                    <td className="py-2.5 px-3 text-emerald-700 font-medium">{sub.governing_station}</td>
                    <td className="py-2.5 px-3 text-[#5c5c5c]">{sub.river_tributary}</td>
                    <td className="py-2.5 px-3 text-right font-mono font-bold">
                      <span className={isDirectSink ? "text-[#0f7b0f]" : "text-[#0067b8]"}>
                        {sub.downstream}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── 3. REACH ROUTING PROGRESSION SPECIFICATION TABLE ─────────────── */}
      <div className="bg-[#ffffff] border border-[#e5e5e5] rounded-lg p-5 shadow-xs">
        <div className="pb-4 border-b border-[#f0f0f0]">
          <h2 className="text-sm font-bold text-[#1b1b1b] flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-[#0067b8]" />
            <span>Muskingum Channel Reach Routing Progression Matrix</span>
          </h2>
          <p className="text-xs text-[#5c5c5c] mt-0.5">
            Calibrated travel time and attenuation factors converging to Rajaram Bridge (Sink-1)
          </p>
        </div>

        <div className="overflow-x-auto mt-4">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-[#e5e5e5] text-[#5c5c5c] font-semibold bg-[#fafafa]">
                <th className="py-2.5 px-3">Reach ID</th>
                <th className="py-2.5 px-3">Reach Segment Name</th>
                <th className="py-2.5 px-3">Inflow Contributors</th>
                <th className="py-2.5 px-3">Muskingum K (hr)</th>
                <th className="py-2.5 px-3">Muskingum X</th>
                <th className="py-2.5 px-3">Channel Type</th>
                <th className="py-2.5 px-3 text-right">Destination</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f0f0f0]">
              {REACHES.map((reach) => {
                const isSelected = selectedItem.id === reach.id;
                const isTerminal = reach.id === "R1";

                return (
                  <tr
                    key={reach.id}
                    onClick={() => setSelectedItem({ type: "reach", id: reach.id })}
                    className={`cursor-pointer transition-colors ${
                      isSelected ? "bg-[#f0f7fc] font-semibold text-[#0067b8]" : "hover:bg-[#f7f7f7] text-[#1b1b1b]"
                    }`}
                  >
                    <td className="py-2.5 px-3 font-mono font-bold">{reach.id}</td>
                    <td className="py-2.5 px-3">{reach.name}</td>
                    <td className="py-2.5 px-3 font-mono text-emerald-700">{reach.inflows}</td>
                    <td className="py-2.5 px-3 font-mono font-bold text-[#0067b8]">{reach.k_hr.toFixed(3)}h</td>
                    <td className="py-2.5 px-3 font-mono">{reach.x_factor.toFixed(2)}</td>
                    <td className="py-2.5 px-3 text-[#5c5c5c]">{reach.type}</td>
                    <td className="py-2.5 px-3 text-right font-mono font-bold">
                      <span className={isTerminal ? "text-[#0f7b0f] font-extrabold" : "text-[#0067b8]"}>
                        {reach.downstream}
                      </span>
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

"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Waves, Info, Layers, TrendingUp, Play } from "lucide-react";

export const SUBBASINS = [
  { id: "S6", name: "Gaganbawda Ghat Crest", area_km2: 227.72, cn: 61.78, lag_hr: 55.3, downstream: "Reach R5", downstreamId: "R5", governing_station: "Gaganbawda", elevation: "720m MSL", river_tributary: "Upper Kumbhi River" },
  { id: "S7", name: "Radhanagari Basin Tributary", area_km2: 195.39, cn: 61.28, lag_hr: 56.0, downstream: "Reach R5", downstreamId: "R5", governing_station: "Radhanagari", elevation: "605m MSL", river_tributary: "Bhogawati Headwater" },
  { id: "S9", name: "Kasaba Tarale Mountain Headwater", area_km2: 366.97, cn: 64.31, lag_hr: 86.7, downstream: "Reach R4", downstreamId: "R4", governing_station: "Kasaba Tarale", elevation: "590m MSL", river_tributary: "Tulshi River Valley" },
  { id: "S8", name: "Beed Mid-Catchment Valley", area_km2: 177.44, cn: 65.76, lag_hr: 56.5, downstream: "Reach R2", downstreamId: "R2", governing_station: "Beed", elevation: "565m MSL", river_tributary: "Bhogawati River Mid" },
  { id: "S4", name: "Karanjphen Highland Subbasin", area_km2: 262.00, cn: 61.89, lag_hr: 51.9, downstream: "Reach R3", downstreamId: "R3", governing_station: "Karanjphen", elevation: "640m MSL", river_tributary: "Kasari River Upper" },
  { id: "S5", name: "Bajar Bhogaon Basin", area_km2: 106.39, cn: 60.97, lag_hr: 35.3, downstream: "Reach R3", downstreamId: "R3", governing_station: "Bajar Bhogaon", elevation: "610m MSL", river_tributary: "Kasari River Lower" },
  { id: "S3", name: "Kotoli Upper Catchment", area_km2: 261.32, cn: 64.82, lag_hr: 66.6, downstream: "Reach R1", downstreamId: "R1", governing_station: "Kotoli", elevation: "585m MSL", river_tributary: "Dhamani River" },
  { id: "S2", name: "Sangarul-Balinga Lateral Basin", area_km2: 153.77, cn: 65.74, lag_hr: 52.6, downstream: "Reach R1", downstreamId: "R1", governing_station: "Sangarul", elevation: "572m MSL", river_tributary: "Panchganga Main Stem" },
  { id: "S1", name: "Karveer Lower Basin (Urban Kolhapur)", area_km2: 86.21, cn: 74.85, lag_hr: 35.8, downstream: "Rajaram Bridge (Sink-1)", downstreamId: "Sink-1", governing_station: "Karveer", elevation: "550m MSL", river_tributary: "Direct to Rajaram Weir" },
];

export const REACHES = [
  { id: "R5", name: "Reach R5 (Upper Confluence)", inflows: "Subbasins S6 + S7", downstream: "Reach R2", downstreamId: "R2", k_hr: 4.619, x_factor: 0.20, type: "Natural River Channel", desc: "Combines Gaganbawda and Radhanagari mountain headwaters" },
  { id: "R4", name: "Reach R4 (Tulshi Tributary)", inflows: "Subbasin S9", downstream: "Reach R2", downstreamId: "R2", k_hr: 1.224, x_factor: 0.20, type: "Mountain Tributary Channel", desc: "Fast mountain runoff from Kasaba Tarale valley" },
  { id: "R3", name: "Reach R3 (Kasari Trunk)", inflows: "Subbasins S4 + S5", downstream: "Reach R1 (Shivaji Confluence)", downstreamId: "R1", k_hr: 3.829, x_factor: 0.20, type: "Compound Valley Channel", desc: "Routes combined Karanjphen and Bajar Bhogaon yield" },
  { id: "R2", name: "Reach R2 (Bhogawati Trunk)", inflows: "Reaches R5 + R4 + Subbasin S8", downstream: "Reach R1 (Shivaji Confluence)", downstreamId: "R1", k_hr: 11.827, x_factor: 0.20, type: "Major Alluvial Channel", desc: "Main Bhogawati river arm carrying majority basin flood volume" },
  { id: "R1", name: "Reach R1 (Panchganga Main Stem)", inflows: "Reaches R2 + R3 + Lateral S3 + S2", downstream: "Rajaram Bridge (Sink-1)", downstreamId: "Sink-1", k_hr: 2.899, x_factor: 0.20, type: "Urban Panchganga Reach via Shivaji Bridge", desc: "Main Panchganga river corridor passing Shivaji Bridge staff gauge directly into Rajaram Bridge Weir" },
];

const BRANCH_COLORS: Record<string, { fill: string; stroke: string; bg: string; text: string; light: string }> = {
  bhogawati: { fill: "#059669", stroke: "#059669", bg: "bg-emerald-50", text: "text-emerald-700", light: "#d1fae5" },
  tulshi:    { fill: "#0891b2", stroke: "#0891b2", bg: "bg-cyan-50",    text: "text-cyan-700",    light: "#cffafe" },
  kasari:    { fill: "#2563eb", stroke: "#2563eb", bg: "bg-blue-50",    text: "text-blue-700",    light: "#dbeafe" },
  main:      { fill: "#7c3aed", stroke: "#7c3aed", bg: "bg-violet-50",  text: "text-violet-700",  light: "#ede9fe" },
  sink:      { fill: "#0067b8", stroke: "#0067b8", bg: "bg-sky-50",     text: "text-sky-700",     light: "#e0f2fe" },
};

function getBranch(id: string): string {
  if (["S6", "S7", "R5"].includes(id)) return "bhogawati";
  if (["S9", "R4"].includes(id)) return "tulshi";
  if (["S4", "S5", "R3"].includes(id)) return "kasari";
  if (["S8", "S3", "S2", "R2", "R1", "S1"].includes(id)) return "main";
  return "sink";
}

// SVG node positions (x, y) — laid out as a proper DAG flowing top to bottom
const NODE_POS: Record<string, [number, number]> = {
  S6: [100, 50],  S7: [240, 50],  S9: [420, 50],  S4: [680, 50],  S5: [820, 50],
  R5: [170, 170], R4: [420, 170], S8: [560, 170],  R3: [750, 170],
  R2: [370, 310],
  S3: [620, 310], S2: [760, 310],
  R1: [530, 440],
  S1: [370, 510],
  SINK: [530, 570],
};

const EDGES: { from: string; to: string }[] = [
  { from: "S6", to: "R5" }, { from: "S7", to: "R5" },
  { from: "S9", to: "R4" },
  { from: "S4", to: "R3" }, { from: "S5", to: "R3" },
  { from: "R5", to: "R2" }, { from: "R4", to: "R2" }, { from: "S8", to: "R2" },
  { from: "R3", to: "R1" }, { from: "R2", to: "R1" },
  { from: "S3", to: "R1" }, { from: "S2", to: "R1" },
  { from: "R1", to: "SINK" }, { from: "S1", to: "SINK" },
];

function FlowDiagram({
  selected,
  onSelect,
  isSimulating,
}: {
  selected: string;
  onSelect: (id: string, type: "subbasin" | "reach" | "sink") => void;
  isSimulating: boolean;
}) {
  const W = 940;
  const H = 640;
  const subIds = SUBBASINS.map((s) => s.id);
  const reachIds = REACHES.map((r) => r.id);

  const getType = (id: string): "subbasin" | "reach" | "sink" => {
    if (subIds.includes(id)) return "subbasin";
    if (reachIds.includes(id)) return "reach";
    return "sink";
  };

  const getLabel = (id: string): string => {
    if (id === "SINK") return "Rajaram Bridge";
    const sub = SUBBASINS.find((s) => s.id === id);
    if (sub) return sub.name.split(" ").slice(0, 2).join(" ");
    const r = REACHES.find((r) => r.id === id);
    if (r) return r.name.replace(/Reach R\d+ \(/, "").replace(")", "");
    return id;
  };

  const getDetail = (id: string): string => {
    const sub = SUBBASINS.find((s) => s.id === id);
    if (sub) return `${sub.area_km2.toFixed(0)} km² · CN ${sub.cn.toFixed(1)}`;
    const r = REACHES.find((r) => r.id === id);
    if (r) return `K: ${r.k_hr.toFixed(2)}h · X: ${r.x_factor.toFixed(2)}`;
    if (id === "SINK") return "Terminal Outlet · 1,837 km²";
    return "";
  };

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ minHeight: 400 }}>
      <defs>
        <marker id="arrow-flow" viewBox="0 0 10 6" refX="10" refY="3" markerWidth="8" markerHeight="6" orient="auto">
          <path d="M0,0 L10,3 L0,6 Z" fill="#94a3b8" />
        </marker>
        {Object.entries(BRANCH_COLORS).map(([key, c]) => (
          <React.Fragment key={key}>
            <marker id={`arrow-${key}`} viewBox="0 0 10 6" refX="10" refY="3" markerWidth="8" markerHeight="6" orient="auto">
              <path d="M0,0 L10,3 L0,6 Z" fill={c.stroke} fillOpacity={0.7} />
            </marker>
            <linearGradient id={`grad-${key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={c.fill} stopOpacity={0.15} />
              <stop offset="100%" stopColor={c.fill} stopOpacity={0.05} />
            </linearGradient>
          </React.Fragment>
        ))}
        {isSimulating && (
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        )}
      </defs>

      {/* Tier labels */}
      {[
        { y: 25, label: "TIER 1 — Western Ghats Headwater Subbasins" },
        { y: 145, label: "TIER 2 — Intermediate Reaches & Junctions" },
        { y: 285, label: "TIER 3 — Main Panchganga Corridor" },
        { y: 545, label: "TERMINAL SINK" },
      ].map((t) => (
        <text key={t.y} x={12} y={t.y} className="fill-gray-400" fontSize={9} fontWeight={600} letterSpacing={1}>
          {t.label.toUpperCase()}
        </text>
      ))}

      {/* Edges with animated flow */}
      {EDGES.map(({ from, to }) => {
        const [x1, y1] = NODE_POS[from];
        const [x2, y2] = NODE_POS[to];
        const branch = getBranch(from);
        const col = BRANCH_COLORS[branch] ?? BRANCH_COLORS.main;
        const isSelected = selected === from || selected === to;
        const midY = y1 + (y2 - y1) * 0.5;

        const nodeR = to === "SINK" ? 30 : getType(to) === "reach" ? 26 : 22;
        const dy = y2 - midY;
        const dx = x2 - x1;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const endX = x2 - (dx / dist) * nodeR * 0.7;
        const endY = y2 - (dy / dist) * nodeR * 0.7;

        const path = `M${x1},${y1 + 22} C${x1},${midY} ${endX},${midY} ${endX},${endY}`;

        return (
          <g key={`${from}-${to}`}>
            <path
              d={path}
              fill="none"
              stroke={isSelected ? col.stroke : "#cbd5e1"}
              strokeWidth={isSelected ? 3 : 1.8}
              strokeOpacity={isSelected ? 0.9 : 0.5}
              markerEnd={`url(#arrow-${isSelected ? branch : "flow"})`}
            />
            {isSimulating && (
              <circle r={4} fill={col.fill} filter="url(#glow)">
                <animateMotion dur={`${1.5 + Math.random()}s`} repeatCount="indefinite" path={path} />
              </circle>
            )}
          </g>
        );
      })}

      {/* Nodes */}
      {Object.entries(NODE_POS).map(([id, [cx, cy]]) => {
        const type = getType(id);
        const branch = getBranch(id);
        const col = id === "SINK" ? BRANCH_COLORS.sink : BRANCH_COLORS[branch];
        const isSel = selected === id;
        const isSink = id === "SINK";
        const isReach = type === "reach";
        const r = isSink ? 32 : isReach ? 26 : 22;

        return (
          <g
            key={id}
            onClick={() => onSelect(id === "SINK" ? "Sink-1" : id, type)}
            className="cursor-pointer"
            role="button"
            tabIndex={0}
          >
            {/* Glow ring on selection */}
            {isSel && (
              <circle cx={cx} cy={cy} r={r + 6} fill="none" stroke={col.stroke} strokeWidth={2} strokeOpacity={0.3}>
                <animate attributeName="r" values={`${r + 4};${r + 8};${r + 4}`} dur="2s" repeatCount="indefinite" />
              </circle>
            )}

            {/* Background circle */}
            <circle
              cx={cx} cy={cy} r={r}
              fill={isSel ? col.fill : "white"}
              stroke={col.stroke}
              strokeWidth={isSel ? 2.5 : 1.5}
              strokeOpacity={isSel ? 1 : 0.6}
            />

            {/* ID label */}
            <text
              x={cx} y={cy - (isSink ? 6 : 3)}
              textAnchor="middle"
              fontSize={isSink ? 11 : isReach ? 10 : 9}
              fontWeight={700}
              fontFamily="monospace"
              fill={isSel ? "white" : col.fill}
            >
              {id === "SINK" ? "SINK" : id}
            </text>

            {/* Small detail below ID */}
            {!isSink && (
              <text
                x={cx} y={cy + 8}
                textAnchor="middle"
                fontSize={7}
                fill={isSel ? "rgba(255,255,255,0.8)" : "#94a3b8"}
                fontFamily="monospace"
              >
                {SUBBASINS.find((s) => s.id === id)
                  ? `${SUBBASINS.find((s) => s.id === id)!.area_km2.toFixed(0)} km²`
                  : REACHES.find((r) => r.id === id)
                  ? `K=${REACHES.find((r) => r.id === id)!.k_hr.toFixed(1)}h`
                  : ""}
              </text>
            )}

            {isSink && (
              <text x={cx} y={cy + 10} textAnchor="middle" fontSize={7} fill={isSel ? "rgba(255,255,255,0.8)" : "#64748b"} fontFamily="monospace">
                1,837 km²
              </text>
            )}

            {/* Hover tooltip label positioned below node */}
            <text
              x={cx} y={cy + r + 14}
              textAnchor="middle"
              fontSize={8}
              fill="#64748b"
              fontWeight={500}
            >
              {getLabel(id)}
            </text>
          </g>
        );
      })}

      {/* Shivaji Bridge marker on R1 */}
      <g>
        <rect x={NODE_POS.R1[0] + 30} y={NODE_POS.R1[1] - 10} width={90} height={20} rx={4} fill="#fef3c7" stroke="#f59e0b" strokeWidth={1} />
        <text x={NODE_POS.R1[0] + 75} y={NODE_POS.R1[1] + 3} textAnchor="middle" fontSize={8} fontWeight={600} fill="#92400e">
          Shivaji Bridge
        </text>
      </g>

      {/* Legend */}
      <g transform="translate(12, 600)">
        {Object.entries({ bhogawati: "Bhogawati Arm", tulshi: "Tulshi Arm", kasari: "Kasari Arm", main: "Main Stem", sink: "Terminal Sink" }).map(
          ([key, label], i) => (
            <g key={key} transform={`translate(${i * 150}, 0)`}>
              <circle cx={6} cy={6} r={5} fill={BRANCH_COLORS[key].fill} fillOpacity={0.8} />
              <text x={16} y={10} fontSize={9} fill="#64748b" fontWeight={500}>
                {label}
              </text>
            </g>
          )
        )}
      </g>
    </svg>
  );
}

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

  const peakQ = summary?.outlet?.peak_discharge_m3s ?? 0;
  const totalVolMcm = summary?.outlet?.total_volume_mcm ?? 0;
  const leadHours = summary?.outlet?.lead_hours_to_peak ?? 0;

  const currentSelectedSubbasin = SUBBASINS.find((s) => s.id === selectedItem.id);
  const currentSelectedReach = REACHES.find((r) => r.id === selectedItem.id);

  const handleSelect = useCallback((id: string, type: "subbasin" | "reach" | "sink") => {
    setSelectedItem({ type, id });
  }, []);

  return (
    <div className="space-y-6">
      {/* INTERACTIVE SVG FLOW DIAGRAM */}
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
              onClick={() => { setIsSimulating(true); setTimeout(() => setIsSimulating(false), 6000); }}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded border transition-all ${
                isSimulating
                  ? "bg-[#0067b8] text-white border-[#0067b8]"
                  : "bg-white text-[#0067b8] border-[#d2d2d2] hover:border-[#0067b8]"
              }`}
            >
              <Play className={`w-3.5 h-3.5 ${isSimulating ? "animate-spin" : ""}`} />
              <span>{isSimulating ? "Simulating Flow..." : "Simulate Flow Pulse"}</span>
            </button>
            <div className="text-xs font-mono font-bold text-[#0067b8] bg-[#f0f7fc] border border-[#d0e5f7] px-3 py-1 rounded">
              Terminal Sink: Rajaram Bridge (RJKT)
            </div>
          </div>
        </div>

        {/* SVG Flow Map */}
        <div className="mt-4 p-4 rounded-lg bg-gradient-to-b from-[#f9fafb] to-[#f0f7fc] border border-[#e2e8f0] overflow-x-auto">
          <div className="min-w-[900px]">
            <FlowDiagram
              selected={selectedItem.id === "Sink-1" ? "SINK" : selectedItem.id}
              onSelect={handleSelect}
              isSimulating={isSimulating}
            />
          </div>
        </div>

        {/* Terminal Sink Metrics */}
        <div className="mt-4 p-4 rounded-xl border-2 border-[#0067b8] bg-[#f0f7fc] flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#0067b8] to-[#004e8c] flex items-center justify-center text-white shadow-sm shrink-0">
              <Waves className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-white bg-[#0067b8] px-2 py-0.5 rounded">
                  TERMINAL MODEL SINK
                </span>
                <span className="text-[10px] text-[#0f7b0f] font-mono font-bold">SINK-1</span>
              </div>
              <h3 className="text-sm font-bold text-[#1b1b1b] mt-0.5">
                Rajaram Bridge &amp; K.T. Weir (Kasba Bawada)
              </h3>
              <p className="text-[11px] text-[#5c5c5c]">
                Total Panchganga Basin drainage confluence (1,837.21 km²)
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 font-mono text-xs">
            <div className="bg-white p-3 rounded-lg border border-[#d0e5f7] text-center min-w-[90px]">
              <div className="text-[9px] text-[#767676] uppercase">Peak Q</div>
              <div className="text-base font-bold text-[#0067b8] mt-0.5">
                {peakQ > 0 ? `${peakQ.toFixed(0)}` : "—"} <span className="text-[10px] font-normal">m³/s</span>
              </div>
            </div>
            <div className="bg-white p-3 rounded-lg border border-[#d0e5f7] text-center min-w-[90px]">
              <div className="text-[9px] text-[#767676] uppercase">Lead Time</div>
              <div className="text-base font-bold text-[#9d5d00] mt-0.5">
                T+{leadHours}h
              </div>
            </div>
            <div className="bg-white p-3 rounded-lg border border-[#d0e5f7] text-center min-w-[90px]">
              <div className="text-[9px] text-[#767676] uppercase">90h Volume</div>
              <div className="text-base font-bold text-[#0f7b0f] mt-0.5">
                {totalVolMcm.toFixed(1)} <span className="text-[10px] font-normal">MCM</span>
              </div>
            </div>
          </div>
        </div>

        {/* Inspection Card */}
        {(currentSelectedSubbasin || currentSelectedReach || selectedItem.id === "Sink-1") && (
          <div className="mt-4 p-4 rounded-lg bg-[#f9fafb] border border-[#e5e5e5] text-xs">
            <div className="font-bold text-[#1b1b1b] flex items-center justify-between mb-3">
              <span className="flex items-center gap-1.5 text-[#0067b8]">
                <Info className="w-4 h-4" />
                <span>
                  {selectedItem.type === "sink"
                    ? "Terminal Sink: Rajaram Bridge (SINK-1)"
                    : `${selectedItem.type.toUpperCase()} [${selectedItem.id}]`}
                </span>
              </span>
              <span className="text-[11px] text-[#767676] font-mono">Basin_1.basin</span>
            </div>

            {currentSelectedSubbasin && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                <div><span className="text-[#767676]">Name: </span><span className="font-bold text-[#1b1b1b]">{currentSelectedSubbasin.name}</span></div>
                <div><span className="text-[#767676]">Area: </span><span className="font-bold text-[#0067b8]">{currentSelectedSubbasin.area_km2.toFixed(2)} km²</span></div>
                <div><span className="text-[#767676]">CN: </span><span className="font-bold text-[#1b1b1b]">{currentSelectedSubbasin.cn.toFixed(2)}</span></div>
                <div><span className="text-[#767676]">Lag: </span><span className="font-bold text-[#9d5d00]">{currentSelectedSubbasin.lag_hr.toFixed(1)} hrs</span></div>
                <div><span className="text-[#767676]">Station: </span><span className="font-bold text-emerald-700">{currentSelectedSubbasin.governing_station}</span></div>
                <div><span className="text-[#767676]">Elevation: </span><span className="font-bold text-[#1b1b1b]">{currentSelectedSubbasin.elevation}</span></div>
                <div><span className="text-[#767676]">Tributary: </span><span className="font-bold text-[#1b1b1b]">{currentSelectedSubbasin.river_tributary}</span></div>
                <div><span className="text-[#767676]">Drains to: </span><span className="font-bold text-[#0067b8]">{currentSelectedSubbasin.downstream}</span></div>
              </div>
            )}

            {currentSelectedReach && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                <div><span className="text-[#767676]">Reach: </span><span className="font-bold text-[#1b1b1b]">{currentSelectedReach.name}</span></div>
                <div><span className="text-[#767676]">Muskingum K: </span><span className="font-bold text-[#0067b8]">{currentSelectedReach.k_hr.toFixed(3)} hrs</span></div>
                <div><span className="text-[#767676]">X Factor: </span><span className="font-bold text-[#1b1b1b]">{currentSelectedReach.x_factor.toFixed(2)}</span></div>
                <div><span className="text-[#767676]">Inflows: </span><span className="font-bold text-emerald-700">{currentSelectedReach.inflows}</span></div>
                <div><span className="text-[#767676]">Destination: </span><span className="font-bold text-[#0067b8]">{currentSelectedReach.downstream}</span></div>
                <div><span className="text-[#767676]">Channel: </span><span className="font-bold text-[#1b1b1b]">{currentSelectedReach.type}</span></div>
                <div className="col-span-2"><span className="text-[#767676]">Description: </span><span className="font-semibold text-[#1b1b1b]">{currentSelectedReach.desc}</span></div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* SUBBASIN TABLE */}
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
            Total Basin Drainage: 1,837.21 km²
          </div>
        </div>

        <div className="overflow-x-auto mt-4">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-[#e5e5e5] text-[#5c5c5c] font-semibold bg-[#fafafa]">
                <th className="py-2.5 px-3">Subbasin</th>
                <th className="py-2.5 px-3">Name</th>
                <th className="py-2.5 px-3">Area (km²)</th>
                <th className="py-2.5 px-3">CN</th>
                <th className="py-2.5 px-3">Lag (hr)</th>
                <th className="py-2.5 px-3">Station</th>
                <th className="py-2.5 px-3">Tributary</th>
                <th className="py-2.5 px-3 text-right">Drains To</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f0f0f0]">
              {SUBBASINS.map((sub) => {
                const isSel = selectedItem.id === sub.id;
                const branch = getBranch(sub.id);
                const col = BRANCH_COLORS[branch];
                return (
                  <tr
                    key={sub.id}
                    onClick={() => setSelectedItem({ type: "subbasin", id: sub.id })}
                    className={`cursor-pointer transition-colors ${isSel ? "font-semibold" : "hover:bg-[#f7f7f7] text-[#1b1b1b]"}`}
                    style={isSel ? { backgroundColor: col.light } : undefined}
                  >
                    <td className="py-2.5 px-3 font-mono font-bold" style={{ color: col.fill }}>{sub.id}</td>
                    <td className="py-2.5 px-3">{sub.name}</td>
                    <td className="py-2.5 px-3 font-mono">{sub.area_km2.toFixed(2)}</td>
                    <td className="py-2.5 px-3 font-mono">{sub.cn.toFixed(2)}</td>
                    <td className="py-2.5 px-3 font-mono">{sub.lag_hr.toFixed(1)}h</td>
                    <td className="py-2.5 px-3 text-emerald-700 font-medium">{sub.governing_station}</td>
                    <td className="py-2.5 px-3 text-[#5c5c5c]">{sub.river_tributary}</td>
                    <td className="py-2.5 px-3 text-right font-mono font-bold" style={{ color: sub.id === "S1" ? "#0f7b0f" : col.fill }}>
                      {sub.downstream}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* REACH TABLE */}
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
                <th className="py-2.5 px-3">Reach</th>
                <th className="py-2.5 px-3">Segment Name</th>
                <th className="py-2.5 px-3">Inflows</th>
                <th className="py-2.5 px-3">K (hr)</th>
                <th className="py-2.5 px-3">X</th>
                <th className="py-2.5 px-3">Channel Type</th>
                <th className="py-2.5 px-3 text-right">Destination</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f0f0f0]">
              {REACHES.map((reach) => {
                const isSel = selectedItem.id === reach.id;
                const branch = getBranch(reach.id);
                const col = BRANCH_COLORS[branch];
                return (
                  <tr
                    key={reach.id}
                    onClick={() => setSelectedItem({ type: "reach", id: reach.id })}
                    className={`cursor-pointer transition-colors ${isSel ? "font-semibold" : "hover:bg-[#f7f7f7] text-[#1b1b1b]"}`}
                    style={isSel ? { backgroundColor: col.light } : undefined}
                  >
                    <td className="py-2.5 px-3 font-mono font-bold" style={{ color: col.fill }}>{reach.id}</td>
                    <td className="py-2.5 px-3">{reach.name}</td>
                    <td className="py-2.5 px-3 font-mono text-emerald-700">{reach.inflows}</td>
                    <td className="py-2.5 px-3 font-mono font-bold" style={{ color: col.fill }}>{reach.k_hr.toFixed(3)}h</td>
                    <td className="py-2.5 px-3 font-mono">{reach.x_factor.toFixed(2)}</td>
                    <td className="py-2.5 px-3 text-[#5c5c5c]">{reach.type}</td>
                    <td className="py-2.5 px-3 text-right font-mono font-bold" style={{ color: reach.id === "R1" ? "#0f7b0f" : col.fill }}>
                      {reach.downstream}
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

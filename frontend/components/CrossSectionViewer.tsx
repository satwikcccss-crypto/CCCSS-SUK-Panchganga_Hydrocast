"use client";
// frontend/components/CrossSectionViewer.tsx
// Interactive 2D River Cross-Section & Hydraulic Water Level Simulation Viewer (HEC-RAS Style)

import React, { useState, useMemo, useEffect, useRef } from "react";
import { SHIVAJI_SURVEY_POINTS, RAJARAM_SURVEY_POINTS } from "@/lib/hydraulics";

interface CrossSectionViewerProps {
  bridgeShivaji?: any;
  bridgeRajaram?: any;
  defaultSite?: "SHIVAJI_BRIDGE" | "RAJARAM_BRIDGE";
}

interface StationPt {
  station: number;
  elevation: number;
}

export default function CrossSectionViewer({
  bridgeShivaji,
  bridgeRajaram,
  defaultSite = "SHIVAJI_BRIDGE",
}: CrossSectionViewerProps) {
  const [selectedSite, setSelectedSite] = useState<"SHIVAJI_BRIDGE" | "RAJARAM_BRIDGE">(defaultSite);
  const [selectedHour, setSelectedHour] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [hoverPt, setHoverPt] = useState<{ x: number; y: number; station: number; elevation: number } | null>(null);
  const animRef = useRef<NodeJS.Timeout | null>(null);

  // Playback timer
  useEffect(() => {
    if (isPlaying) {
      animRef.current = setInterval(() => {
        setSelectedHour((prev) => (prev >= 89 ? 0 : prev + 1));
      }, 350);
    } else if (animRef.current) {
      clearInterval(animRef.current);
    }
    return () => {
      if (animRef.current) clearInterval(animRef.current);
    };
  }, [isPlaying]);

  // Site Configuration & Thresholds
  const siteConfig = useMemo(() => {
    if (selectedSite === "SHIVAJI_BRIDGE") {
      const site = bridgeShivaji?.site ?? {};
      return {
        id: "SHIVAJI_BRIDGE",
        name: site.site_name ?? "Chhatrapati Shivaji Maharaj Bridge",
        river: site.river_name ?? "Panchganga River",
        reach: "Panchganga Ghat (Kolhapur Urban)",
        rawPoints: SHIVAJI_SURVEY_POINTS,
        bankLeftStation: 124.29,
        bankRightStation: 261.66,
        alertStage: site.alert_stage_m ?? 542.10,
        warningStage: site.warning_stage_m ?? 542.70,
        dangerStage: site.danger_stage_m ?? 543.30,
        extremeStage: site.extreme_stage_m ?? 544.00,
        hflStage: site.hfl_m ?? 545.33,
        sensorDeckElevation: 549.35,
        forecast: bridgeShivaji?.forecast ?? [],
        siteInfo: site,
      };
    } else {
      const site = bridgeRajaram?.site ?? {};
      return {
        id: "RAJARAM_BRIDGE",
        name: site.site_name ?? "Rajaram K.T. Weir (Kasba Bawada)",
        river: site.river_name ?? "Panchganga River",
        reach: "Kasba Bawada Barrage",
        rawPoints: RAJARAM_SURVEY_POINTS,
        bankLeftStation: 79.87,
        bankRightStation: 342.96,
        alertStage: site.alert_stage_m ?? 541.50,
        warningStage: site.warning_stage_m ?? 542.07,
        dangerStage: site.danger_stage_m ?? 543.30,
        extremeStage: site.extreme_stage_m ?? 544.00,
        hflStage: site.hfl_m ?? 545.33,
        forecast: bridgeRajaram?.forecast ?? [],
        siteInfo: site,
      };
    }
  }, [selectedSite, bridgeShivaji, bridgeRajaram]);

  // Convert Survey Points to 2D Cross Section [Station (m), Elevation (m MSL)]
  const crossSectionPoints: StationPt[] = useMemo(() => {
    const raw = siteConfig.rawPoints;
    if (!raw || raw.length === 0) return [];
    
    let cumDist = 0;
    const pts: StationPt[] = [{ station: 0, elevation: raw[0][2] }];
    
    for (let i = 1; i < raw.length; i++) {
      const dN = raw[i][0] - raw[i - 1][0];
      const dE = raw[i][1] - raw[i - 1][1];
      const dist = Math.sqrt(dN * dN + dE * dE);
      cumDist += dist;
      pts.push({
        station: parseFloat(cumDist.toFixed(2)),
        elevation: parseFloat(raw[i][2].toFixed(3)),
      });
    }
    return pts;
  }, [siteConfig]);

  // Current Forecast State at selected hour
  const currentForecast = useMemo(() => {
    const fc = siteConfig.forecast[selectedHour];
    if (fc) {
      return {
        stage_m: fc.stage_m,
        discharge_m3s: fc.discharge_m3s,
        alert_level: fc.alert_level || "NORMAL",
        time: fc.forecast_time,
      };
    }
    // Fallback baseline
    const baseStage = selectedSite === "SHIVAJI_BRIDGE" ? 541.02 : 533.40;
    return {
      stage_m: baseStage,
      discharge_m3s: selectedSite === "SHIVAJI_BRIDGE" ? 108.0 : 82.0,
      alert_level: "NORMAL",
      time: new Date().toISOString(),
    };
  }, [siteConfig, selectedHour, selectedSite]);

  // Geometry Bounds & Scales
  const bounds = useMemo(() => {
    if (crossSectionPoints.length === 0) {
      return { minX: 0, maxX: 400, minY: 525, maxY: 550 };
    }
    const xs = crossSectionPoints.map((p) => p.station);
    const ys = crossSectionPoints.map((p) => p.elevation);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.floor(Math.min(...ys) - 1.5);
    const maxY = Math.ceil(Math.max(...ys, siteConfig.hflStage + 1.0));
    return { minX, maxX, minY, maxY };
  }, [crossSectionPoints, siteConfig]);

  // SVG Dimensions & Padding
  const svgWidth = 850;
  const svgHeight = 360;
  const pad = { top: 35, right: 90, bottom: 45, left: 65 };
  const plotW = svgWidth - pad.left - pad.right;
  const plotH = svgHeight - pad.top - pad.bottom;

  // Coordinate Mapping
  const toSvgX = (st: number) =>
    pad.left + ((st - bounds.minX) / (bounds.maxX - bounds.minX)) * plotW;
  const toSvgY = (el: number) =>
    pad.top + ((bounds.maxY - el) / (bounds.maxY - bounds.minY)) * plotH;
  const fromSvgX = (px: number) =>
    bounds.minX + ((px - pad.left) / plotW) * (bounds.maxX - bounds.minX);

  // Ground Path SVG String
  const groundPathD = useMemo(() => {
    if (crossSectionPoints.length === 0) return "";
    return crossSectionPoints
      .map((p, i) => `${i === 0 ? "M" : "L"} ${toSvgX(p.station)} ${toSvgY(p.elevation)}`)
      .join(" ");
  }, [crossSectionPoints, bounds]);

  // Subsurface Ground Fill (Below bed)
  const groundFillD = useMemo(() => {
    if (crossSectionPoints.length === 0) return "";
    const first = crossSectionPoints[0];
    const last = crossSectionPoints[crossSectionPoints.length - 1];
    const bottomY = toSvgY(bounds.minY);
    return `${groundPathD} L ${toSvgX(last.station)} ${bottomY} L ${toSvgX(first.station)} ${bottomY} Z`;
  }, [crossSectionPoints, groundPathD, bounds]);

  // Water Polygon Fill calculation for current water stage
  const waterPolygonD = useMemo(() => {
    const wse = currentForecast.stage_m;
    if (crossSectionPoints.length === 0) return "";

    // Find intersection segments where ground elevation is below water surface
    const wetSegments: Array<Array<[number, number]>> = [];
    let currentSegment: Array<[number, number]> = [];

    for (let i = 0; i < crossSectionPoints.length - 1; i++) {
      const p1 = crossSectionPoints[i];
      const p2 = crossSectionPoints[i + 1];

      const p1Below = p1.elevation <= wse;
      const p2Below = p2.elevation <= wse;

      if (p1Below && p2Below) {
        if (currentSegment.length === 0) {
          currentSegment.push([p1.station, p1.elevation]);
        }
        currentSegment.push([p2.station, p2.elevation]);
      } else if (p1Below && !p2Below) {
        // Exiting water
        const frac = (wse - p1.elevation) / (p2.elevation - p1.elevation);
        const xInt = p1.station + frac * (p2.station - p1.station);
        if (currentSegment.length === 0) currentSegment.push([p1.station, p1.elevation]);
        currentSegment.push([xInt, wse]);
        wetSegments.push(currentSegment);
        currentSegment = [];
      } else if (!p1Below && p2Below) {
        // Entering water
        const frac = (wse - p1.elevation) / (p2.elevation - p1.elevation);
        const xInt = p1.station + frac * (p2.station - p1.station);
        currentSegment = [[xInt, wse], [p2.station, p2.elevation]];
      }
    }

    if (currentSegment.length > 0) {
      wetSegments.push(currentSegment);
    }

    if (wetSegments.length === 0) return "";

    // Construct SVG path for each wet segment: Ground points + top horizontal line
    return wetSegments
      .map((seg) => {
        const firstPt = seg[0];
        const lastPt = seg[seg.length - 1];
        const bedPath = seg.map((pt) => `L ${toSvgX(pt[0])} ${toSvgY(pt[1])}`).join(" ");
        return `M ${toSvgX(firstPt[0])} ${toSvgY(wse)} ${bedPath} L ${toSvgX(lastPt[0])} ${toSvgY(wse)} Z`;
      })
      .join(" ");
  }, [crossSectionPoints, currentForecast.stage_m, bounds]);

  // Hydraulic Metrics for Current Water Level
  const hydraulicStats = useMemo(() => {
    const wse = currentForecast.stage_m;
    let minBed = 9999;
    let wettedArea = 0;
    let topWidth = 0;

    for (let i = 0; i < crossSectionPoints.length - 1; i++) {
      const p1 = crossSectionPoints[i];
      const p2 = crossSectionPoints[i + 1];
      minBed = Math.min(minBed, p1.elevation, p2.elevation);

      const d1 = Math.max(0, wse - p1.elevation);
      const d2 = Math.max(0, wse - p2.elevation);

      if (d1 > 0 || d2 > 0) {
        const dx = p2.station - p1.station;
        if (d1 > 0 && d2 > 0) {
          wettedArea += 0.5 * (d1 + d2) * dx;
          topWidth += dx;
        } else if (d1 > 0 && d2 === 0) {
          const frac = d1 / (p1.elevation - p2.elevation + d1);
          wettedArea += 0.5 * d1 * (dx * frac);
          topWidth += dx * frac;
        } else if (d1 === 0 && d2 > 0) {
          const frac = d2 / (p2.elevation - p1.elevation + d2);
          wettedArea += 0.5 * d2 * (dx * frac);
          topWidth += dx * frac;
        }
      }
    }

    const maxDepth = Math.max(0, wse - minBed);
    const freeboardWarning = siteConfig.warningStage - wse;
    const freeboardDanger = siteConfig.dangerStage - wse;

    return {
      minBed: minBed === 9999 ? 0 : minBed,
      maxDepth,
      topWidth,
      wettedArea,
      freeboardWarning,
      freeboardDanger,
    };
  }, [crossSectionPoints, currentForecast.stage_m, siteConfig]);

  // Alert Badge Style
  const alertBadge = useMemo(() => {
    const wse = currentForecast.stage_m;
    if (wse >= siteConfig.hflStage) {
      return { label: "HFL EXCEEDED", bg: "bg-purple-50", text: "text-purple-700", border: "border-purple-200" };
    }
    if (wse >= siteConfig.extremeStage) {
      return { label: "EXTREME FLOOD", bg: "bg-rose-50", text: "text-rose-700", border: "border-rose-200" };
    }
    if (wse >= siteConfig.dangerStage) {
      return { label: "DANGER LEVEL", bg: "bg-red-50", text: "text-red-700", border: "border-red-200" };
    }
    if (wse >= siteConfig.warningStage) {
      return { label: "WARNING LEVEL", bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200" };
    }
    if (wse >= (siteConfig.alertStage ?? siteConfig.warningStage - 2.0)) {
      return { label: "ALERT STAGE", bg: "bg-yellow-50", text: "text-yellow-800", border: "border-yellow-200" };
    }
    return { label: "NORMAL STAGE", bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" };
  }, [currentForecast.stage_m, siteConfig]);

  // Projected Threshold Breach Timing
  const arrivalInfo = useMemo(() => {
    const fc = siteConfig.forecast;
    const breached = fc.find((f: any) => f.alert_level && f.alert_level !== "NORMAL");
    if (breached) {
      return {
        hasBreach: true,
        text: `T+${breached.lead_hours}h (${new Date(breached.forecast_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} UTC)`,
        level: breached.alert_level,
      };
    }
    return {
      hasBreach: false,
      text: "No threshold breach projected in 90-hour forecast window",
      level: "NORMAL",
    };
  }, [siteConfig.forecast]);

  const hflSafetyMargin = siteConfig.hflStage - currentForecast.stage_m;

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden font-sans text-gray-800 mb-6">
      {/* ── Top HEC-RAS & Bridge Station Header ─────────────────────────────── */}
      <div className="bg-gray-50 px-5 py-3.5 border-b border-gray-200 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-50 text-blue-600 border border-blue-200 text-xs font-bold font-mono-code shadow-xs">
            2D
          </span>
          <div>
            <div className="text-sm font-bold text-gray-900 flex items-center gap-2">
              <span>{siteConfig.name}</span>
              <span className="text-[11px] font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-200 font-mono-code">
                {selectedSite === "SHIVAJI_BRIDGE" ? "Shivaji Ghat Reach" : "Kasba Bawada Barrage Reach"}
              </span>
            </div>
            <div className="text-[11px] text-gray-500 mt-0.5">
              River Gauge Station · <span className="text-gray-700 font-semibold font-mono-code">{selectedSite === "SHIVAJI_BRIDGE" ? "16.7089°N, 74.2193°E" : "16.7362°N, 74.2359°E"}</span> | River:{" "}
              <span className="text-gray-700 font-semibold">{siteConfig.river}</span> | Datum:{" "}
              <span className="text-gray-700 font-semibold">MSL</span>
            </div>
          </div>
        </div>

        {/* Site Switcher Toggle Buttons & Live Status */}
        <div className="flex items-center gap-3">
          <div className="bg-gray-200/80 p-1 rounded-lg border border-gray-200 flex items-center shadow-inner">
            <button
              onClick={() => {
                setSelectedSite("SHIVAJI_BRIDGE");
                setSelectedHour(0);
              }}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                selectedSite === "SHIVAJI_BRIDGE"
                  ? "bg-white text-gray-900 shadow-sm border border-gray-200"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              Shivaji Bridge
            </button>
            <button
              onClick={() => {
                setSelectedSite("RAJARAM_BRIDGE");
                setSelectedHour(0);
              }}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                selectedSite === "RAJARAM_BRIDGE"
                  ? "bg-white text-gray-900 shadow-sm border border-gray-200"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              Rajaram Weir
            </button>
          </div>

          <div
            className={`px-3 py-1.5 rounded-lg text-xs font-bold font-mono-code uppercase tracking-wider border shadow-xs ${alertBadge.bg} ${alertBadge.text} ${alertBadge.border}`}
          >
            ● {alertBadge.label}
          </div>
        </div>
      </div>

      {/* ── Fused Bridge Flood Thresholds & Safety Clearance Banner ───────────── */}
      <div className="bg-white px-5 py-3 border-b border-gray-200 flex flex-wrap items-center justify-between gap-3 text-xs">
        {/* 4 Standard Threshold Levels */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="px-2.5 py-1 bg-yellow-50 border border-yellow-200 rounded-md flex items-center gap-1.5">
            <span className="text-[10px] font-bold text-yellow-800 uppercase">Alert</span>
            <span className="font-extrabold text-yellow-900 font-mono-code">{siteConfig.alertStage.toFixed(2)}m</span>
          </div>
          <div className="px-2.5 py-1 bg-amber-50 border border-amber-200 rounded-md flex items-center gap-1.5">
            <span className="text-[10px] font-bold text-amber-800 uppercase">Warning</span>
            <span className="font-extrabold text-amber-900 font-mono-code">{siteConfig.warningStage.toFixed(2)}m</span>
          </div>
          <div className="px-2.5 py-1 bg-rose-50 border border-rose-200 rounded-md flex items-center gap-1.5">
            <span className="text-[10px] font-bold text-rose-800 uppercase">Danger</span>
            <span className="font-extrabold text-rose-900 font-mono-code">{siteConfig.dangerStage.toFixed(2)}m</span>
          </div>
          <div className="px-2.5 py-1 bg-purple-50 border border-purple-200 rounded-md flex items-center gap-1.5">
            <span className="text-[10px] font-bold text-purple-800 uppercase">HFL</span>
            <span className="font-extrabold text-purple-900 font-mono-code">{siteConfig.hflStage.toFixed(2)}m</span>
          </div>
        </div>

        {/* HFL Safety Margin & Breach Timing */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-gray-50 border border-gray-200">
            <span className="text-gray-500 font-medium">HFL Clearance:</span>
            <span
              className={`font-extrabold font-mono-code ${
                hflSafetyMargin <= 0 ? "text-rose-600" : hflSafetyMargin <= 1.5 ? "text-amber-600" : "text-emerald-600"
              }`}
            >
              {hflSafetyMargin <= 0 ? `+${Math.abs(hflSafetyMargin).toFixed(2)}m (BREACHED)` : `${hflSafetyMargin.toFixed(2)}m`}
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-gray-600">
            <span className="font-semibold text-gray-800">Threshold Timing:</span>
            <span className={arrivalInfo.hasBreach ? "font-bold text-amber-700 font-mono-code" : "text-gray-500 font-mono-code"}>
              {arrivalInfo.text}
            </span>
          </div>
        </div>
      </div>

      {/* ── Real-Time Hydraulic Telemetry Bar ──────────────────────────────── */}
      <div className="bg-gray-50/70 px-5 py-2.5 border-b border-gray-200 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs font-mono-code">
        <div className="bg-white p-2.5 rounded-lg border border-gray-200 shadow-xs">
          <div className="text-[10px] text-gray-500 font-sans font-semibold uppercase">Water Stage (WSE)</div>
          <div className="text-base font-bold text-blue-600 mt-0.5">
            {currentForecast.stage_m.toFixed(2)} <span className="text-[11px] font-normal text-gray-400">m MSL</span>
          </div>
        </div>
        <div className="bg-white p-2.5 rounded-lg border border-gray-200 shadow-xs">
          <div className="text-[10px] text-gray-500 font-sans font-semibold uppercase">River Discharge (Q)</div>
          <div className="text-base font-bold text-indigo-600 mt-0.5">
            {currentForecast.discharge_m3s.toFixed(1)} <span className="text-[11px] font-normal text-gray-400">m³/s</span>
          </div>
        </div>
        <div className="bg-white p-2.5 rounded-lg border border-gray-200 shadow-xs">
          <div className="text-[10px] text-gray-500 font-sans font-semibold uppercase">Max Water Depth</div>
          <div className="text-base font-bold text-cyan-600 mt-0.5">
            {hydraulicStats.maxDepth.toFixed(2)} <span className="text-[11px] font-normal text-gray-400">m</span>
          </div>
        </div>
        <div className="bg-white p-2.5 rounded-lg border border-gray-200 shadow-xs">
          <div className="text-[10px] text-gray-500 font-sans font-semibold uppercase">Top Surface Width</div>
          <div className="text-base font-bold text-teal-600 mt-0.5">
            {hydraulicStats.topWidth.toFixed(1)} <span className="text-[11px] font-normal text-gray-400">m</span>
          </div>
        </div>
        <div className="bg-white p-2.5 rounded-lg border border-gray-200 shadow-xs">
          <div className="text-[10px] text-gray-500 font-sans font-semibold uppercase">Wetted Flow Area</div>
          <div className="text-base font-bold text-amber-600 mt-0.5">
            {hydraulicStats.wettedArea.toFixed(0)} <span className="text-[11px] font-normal text-gray-400">m²</span>
          </div>
        </div>
        <div className="bg-white p-2.5 rounded-lg border border-gray-200 shadow-xs">
          <div className="text-[10px] text-gray-500 font-sans font-semibold uppercase">Warning Clearance</div>
          <div
            className={`text-base font-extrabold mt-0.5 ${
              hydraulicStats.freeboardWarning <= 0 ? "text-rose-600" : "text-emerald-600"
            }`}
          >
            {hydraulicStats.freeboardWarning <= 0
              ? `+${Math.abs(hydraulicStats.freeboardWarning).toFixed(2)}m`
              : `-${hydraulicStats.freeboardWarning.toFixed(2)}m`}
          </div>
        </div>
      </div>

      {/* ── Interactive 2D Cross Section SVG Canvas ────────────────────────── */}
      <div className="p-4 bg-gray-50 relative">
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className="w-full h-auto max-h-[380px] select-none touch-none"
          onMouseMove={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const mouseX = ((e.clientX - rect.left) / rect.width) * svgWidth;
            const mouseY = ((e.clientY - rect.top) / rect.height) * svgHeight;
            if (mouseX >= pad.left && mouseX <= svgWidth - pad.right && mouseY >= pad.top && mouseY <= svgHeight - pad.bottom) {
              const st = fromSvgX(mouseX);
              // Find closest survey vertex
              let closest = crossSectionPoints[0];
              let minDist = 9999;
              for (const p of crossSectionPoints) {
                const dist = Math.abs(p.station - st);
                if (dist < minDist) {
                  minDist = dist;
                  closest = p;
                }
              }
              setHoverPt({
                x: mouseX,
                y: mouseY,
                station: closest?.station ?? st,
                elevation: closest?.elevation ?? bounds.minY,
              });
            } else {
              setHoverPt(null);
            }
          }}
          onTouchMove={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const touch = e.touches[0];
            const mouseX = ((touch.clientX - rect.left) / rect.width) * svgWidth;
            const mouseY = ((touch.clientY - rect.top) / rect.height) * svgHeight;
            if (mouseX >= pad.left && mouseX <= svgWidth - pad.right && mouseY >= pad.top && mouseY <= svgHeight - pad.bottom) {
              const st = fromSvgX(mouseX);
              let closest = crossSectionPoints[0];
              let minDist = 9999;
              for (const p of crossSectionPoints) {
                const dist = Math.abs(p.station - st);
                if (dist < minDist) {
                  minDist = dist;
                  closest = p;
                }
              }
              setHoverPt({
                x: mouseX,
                y: mouseY,
                station: closest?.station ?? st,
                elevation: closest?.elevation ?? bounds.minY,
              });
            } else {
              setHoverPt(null);
            }
          }}
          onMouseLeave={() => setHoverPt(null)}
          onTouchEnd={() => setHoverPt(null)}
        >
          <defs>
            {/* Water Linear Gradient */}
            <linearGradient id="waterGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.7" />
              <stop offset="100%" stopColor="#0284c7" stopOpacity="0.9" />
            </linearGradient>

            {/* Subsurface Soil Gradient */}
            <linearGradient id="groundGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#e5e7eb" stopOpacity="1" />
              <stop offset="100%" stopColor="#d1d5db" stopOpacity="1" />
            </linearGradient>

            {/* Riverbed Hatch Pattern */}
            <pattern id="bedHatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="8" stroke="#9ca3af" strokeWidth="1" strokeOpacity="0.5" />
            </pattern>
          </defs>

          {/* Background Grid Lines */}
          {Array.from({ length: 6 }).map((_, i) => {
            const el = bounds.minY + ((bounds.maxY - bounds.minY) / 5) * i;
            const yPos = toSvgY(el);
            return (
              <g key={`grid-y-${i}`}>
                <line
                  x1={pad.left}
                  y1={yPos}
                  x2={svgWidth - pad.right}
                  y2={yPos}
                  stroke="#d1d5db"
                  strokeWidth="1"
                  strokeDasharray="3 3"
                />
                <text
                  x={pad.left - 8}
                  y={yPos + 4}
                  textAnchor="end"
                  fill="#6b7280"
                  fontSize="10"
                  fontFamily="monospace"
                >
                  {el.toFixed(1)}
                </text>
              </g>
            );
          })}

          {/* Vertical Grid Lines (Stations in meters) */}
          {Array.from({ length: 9 }).map((_, i) => {
            const st = bounds.minX + ((bounds.maxX - bounds.minX) / 8) * i;
            const xPos = toSvgX(st);
            return (
              <g key={`grid-x-${i}`}>
                <line
                  x1={xPos}
                  y1={pad.top}
                  x2={xPos}
                  y2={svgHeight - pad.bottom}
                  stroke="#e5e7eb"
                  strokeWidth="1"
                  strokeDasharray="3 3"
                />
                <text
                  x={xPos}
                  y={svgHeight - pad.bottom + 16}
                  textAnchor="middle"
                  fill="#6b7280"
                  fontSize="10"
                  fontFamily="monospace"
                >
                  {st.toFixed(0)}m
                </text>
              </g>
            );
          })}

          {/* Ground Subsurface Fill */}
          {groundFillD && <path d={groundFillD} fill="url(#groundGrad)" />}
          {groundFillD && <path d={groundFillD} fill="url(#bedHatch)" />}

          {/* Simulated Water Body Polygon */}
          {waterPolygonD && (
            <path
              d={waterPolygonD}
              fill="url(#waterGrad)"
              stroke="#38bdf8"
              strokeWidth="1.5"
              className="transition-all duration-300 ease-out"
            />
          )}

          {/* Ground Cross-Section Line */}
          {groundPathD && (
            <path
              d={groundPathD}
              fill="none"
              stroke="#6b7280"
              strokeWidth="2.5"
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          )}

          {/* Survey Vertices Points (HEC-RAS style square markers) */}
          {crossSectionPoints.map((p, idx) => {
            const px = toSvgX(p.station);
            const py = toSvgY(p.elevation);
            return (
              <rect
                key={idx}
                x={px - 2}
                y={py - 2}
                width="4"
                height="4"
                fill="#ffffff"
                stroke="#9ca3af"
                strokeWidth="1"
              />
            );
          })}

          {/* Bank Station Markers (Red Dots) */}
          {(() => {
            const leftPt = crossSectionPoints.find((p) => Math.abs(p.station - siteConfig.bankLeftStation) < 2) ?? crossSectionPoints[0];
            const rightPt = crossSectionPoints.find((p) => Math.abs(p.station - siteConfig.bankRightStation) < 2) ?? crossSectionPoints[crossSectionPoints.length - 1];
            return (
              <g>
                {/* Left Bank */}
                {leftPt && (
                  <>
                    <circle
                      cx={toSvgX(leftPt.station)}
                      cy={toSvgY(leftPt.elevation)}
                      r="5"
                      fill="#ef4444"
                      stroke="#ffffff"
                      strokeWidth="1.5"
                    />
                    <text
                      x={toSvgX(leftPt.station)}
                      y={toSvgY(leftPt.elevation) - 10}
                      textAnchor="middle"
                      fill="#f87171"
                      fontSize="9.5"
                      fontWeight="bold"
                      fontFamily="monospace"
                    >
                      Left Bank ({leftPt.elevation.toFixed(2)}m)
                    </text>
                  </>
                )}

                {/* Right Bank */}
                {rightPt && (
                  <>
                    <circle
                      cx={toSvgX(rightPt.station)}
                      cy={toSvgY(rightPt.elevation)}
                      r="5"
                      fill="#ef4444"
                      stroke="#ffffff"
                      strokeWidth="1.5"
                    />
                    <text
                      x={toSvgX(rightPt.station)}
                      y={toSvgY(rightPt.elevation) - 10}
                      textAnchor="middle"
                      fill="#f87171"
                      fontSize="9.5"
                      fontWeight="bold"
                      fontFamily="monospace"
                    >
                      Right Bank ({rightPt.elevation.toFixed(2)}m)
                    </text>
                  </>
                )}
              </g>
            );
          })()}

          {/* ── Reference Flood Alert Level Guide Lines ─────────────────────── */}
          {/* 1. Warning Stage Line (Amber) */}
          <g>
            <line
              x1={pad.left}
              y1={toSvgY(siteConfig.warningStage)}
              x2={svgWidth - pad.right}
              y2={toSvgY(siteConfig.warningStage)}
              stroke="#f59e0b"
              strokeWidth="1.5"
              strokeDasharray="5 3"
            />
            <text
              x={svgWidth - pad.right + 6}
              y={toSvgY(siteConfig.warningStage) + 3}
              fill="#f59e0b"
              fontSize="10"
              fontWeight="bold"
              fontFamily="monospace"
            >
              Warn {siteConfig.warningStage.toFixed(2)}m
            </text>
          </g>

          {/* 2. Danger Stage Line (Rose) */}
          <g>
            <line
              x1={pad.left}
              y1={toSvgY(siteConfig.dangerStage)}
              x2={svgWidth - pad.right}
              y2={toSvgY(siteConfig.dangerStage)}
              stroke="#ef4444"
              strokeWidth="1.5"
              strokeDasharray="5 3"
            />
            <text
              x={svgWidth - pad.right + 6}
              y={toSvgY(siteConfig.dangerStage) + 3}
              fill="#ef4444"
              fontSize="10"
              fontWeight="bold"
              fontFamily="monospace"
            >
              Dang {siteConfig.dangerStage.toFixed(2)}m
            </text>
          </g>

          {/* 3. Highest Flood Level (HFL Line - Purple) */}
          <g>
            <line
              x1={pad.left}
              y1={toSvgY(siteConfig.hflStage)}
              x2={svgWidth - pad.right}
              y2={toSvgY(siteConfig.hflStage)}
              stroke="#a855f7"
              strokeWidth="1.5"
              strokeDasharray="4 2"
            />
            <text
              x={svgWidth - pad.right + 6}
              y={toSvgY(siteConfig.hflStage) + 3}
              fill="#a855f7"
              fontSize="10"
              fontWeight="bold"
              fontFamily="monospace"
            >
              HFL {siteConfig.hflStage.toFixed(2)}m
            </text>
          </g>

          {/* 4. Active Water Surface Level Header Indicator */}
          <g>
            <line
              x1={pad.left}
              y1={toSvgY(currentForecast.stage_m)}
              x2={svgWidth - pad.right}
              y2={toSvgY(currentForecast.stage_m)}
              stroke="#38bdf8"
              strokeWidth="2.5"
            />
            <polygon
              points={`${pad.left - 2},${toSvgY(currentForecast.stage_m)} ${pad.left - 10},${toSvgY(
                currentForecast.stage_m
              ) - 5} ${pad.left - 10},${toSvgY(currentForecast.stage_m) + 5}`}
              fill="#38bdf8"
            />
            <text
              x={pad.left + 10}
              y={toSvgY(currentForecast.stage_m) - 6}
              fill="#38bdf8"
              fontSize="11"
              fontWeight="bold"
              fontFamily="monospace"
            >
              WS (T+{selectedHour}h): {currentForecast.stage_m.toFixed(2)}m MSL | Q:{" "}
              {currentForecast.discharge_m3s.toFixed(1)} m³/s
            </text>
          </g>

          {/* Axis Labels */}
          <text
            x={svgWidth / 2}
            y={svgHeight - 10}
            textAnchor="middle"
            fill="#94a3b8"
            fontSize="11"
            fontWeight="bold"
          >
            Station (m) — Cross Section Transverse Distance
          </text>
          <text
            x={15}
            y={svgHeight / 2}
            textAnchor="middle"
            fill="#94a3b8"
            fontSize="11"
            fontWeight="bold"
            transform={`rotate(-90 15 ${svgHeight / 2})`}
          >
            Elevation (m MSL)
          </text>

          {/* Interactive Mouse Hover Cursor & Measurement */}
          {hoverPt && (
            <g>
              <line
                x1={hoverPt.x}
                y1={pad.top}
                x2={hoverPt.x}
                y2={svgHeight - pad.bottom}
                stroke="#60a5fa"
                strokeWidth="1"
                strokeDasharray="2 2"
              />
              <line
                x1={pad.left}
                y1={toSvgY(hoverPt.elevation)}
                x2={svgWidth - pad.right}
                y2={toSvgY(hoverPt.elevation)}
                stroke="#60a5fa"
                strokeWidth="1"
                strokeDasharray="2 2"
              />
              <circle cx={hoverPt.x} cy={toSvgY(hoverPt.elevation)} r="4" fill="#60a5fa" />
              <rect
                x={Math.min(hoverPt.x + 10, svgWidth - pad.right - 140)}
                y={Math.max(toSvgY(hoverPt.elevation) - 45, pad.top)}
                width="135"
                height="40"
                rx="4"
                fill="#0f172a"
                stroke="#3b82f6"
                strokeWidth="1"
                opacity="0.95"
              />
              <text
                x={Math.min(hoverPt.x + 16, svgWidth - pad.right - 134)}
                y={Math.max(toSvgY(hoverPt.elevation) - 28, pad.top + 16)}
                fill="#f8fafc"
                fontSize="10"
                fontFamily="monospace"
              >
                Station: {hoverPt.station.toFixed(1)}m
              </text>
              <text
                x={Math.min(hoverPt.x + 16, svgWidth - pad.right - 134)}
                y={Math.max(toSvgY(hoverPt.elevation) - 14, pad.top + 30)}
                fill="#38bdf8"
                fontSize="10"
                fontFamily="monospace"
              >
                Bed RL: {hoverPt.elevation.toFixed(2)}m MSL
              </text>
            </g>
          )}

          <g transform={`translate(${svgWidth - pad.right - 145}, ${pad.top + 8})`}>
            <rect
              width="140"
              height="80"
              rx="4"
              fill="#ffffff"
              stroke="#e5e7eb"
              strokeWidth="1"
              opacity="0.95"
            />
            <text x="8" y="15" fill="#4b5563" fontSize="10" fontWeight="bold">
              Legend
            </text>

            <line x1="8" y1="30" x2="28" y2="30" stroke="#4b5563" strokeWidth="2" />
            <text x="32" y="33" fill="#6b7280" fontSize="9">
              Ground Profile
            </text>

            <line x1="8" y1="46" x2="28" y2="46" stroke="#9333ea" strokeWidth="1.5" strokeDasharray="2 2" />
            <text x="32" y="49" fill="#6b7280" fontSize="9">
              Bank Station
            </text>

            <line x1="8" y1="62" x2="28" y2="62" stroke="#0284c7" strokeWidth="2" />
            <text x="32" y="65" fill="#6b7280" fontSize="9">
              Water Level
            </text>
          </g>
        </svg>
      </div>

      {/* ── 90-Hour Interactive Flood Simulation Slider & Animation Controls ── */}
      <div className="bg-gray-50 p-4 border-t border-gray-200 flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Playback Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSelectedHour(0)}
            className="p-2 rounded bg-white hover:bg-gray-100 text-gray-700 border border-gray-300 text-xs font-bold shadow-sm"
            title="Jump to T+0h Start"
          >
            ⏮
          </button>
          <button
            onClick={() => setSelectedHour((prev) => Math.max(0, prev - 1))}
            className="p-2 rounded bg-white hover:bg-gray-100 text-gray-700 border border-gray-300 text-xs font-bold shadow-sm"
            title="Step Back 1h"
          >
            ◀
          </button>
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className={`px-3 py-1.5 rounded flex items-center gap-1.5 text-xs font-bold transition-all shadow-sm ${
              isPlaying
                ? "bg-rose-600 hover:bg-rose-500 text-white"
                : "bg-blue-600 hover:bg-blue-500 text-white"
            }`}
          >
            <span>{isPlaying ? "⏸ Pause" : "▶ Play Hydrograph Wave"}</span>
          </button>
          <button
            onClick={() => setSelectedHour((prev) => Math.min(89, prev + 1))}
            className="p-2 rounded bg-white hover:bg-gray-100 text-gray-700 border border-gray-300 text-xs font-bold shadow-sm"
            title="Step Forward 1h"
          >
            ▶
          </button>
          <button
            onClick={() => setSelectedHour(89)}
            className="p-2 rounded bg-white hover:bg-gray-100 text-gray-700 border border-gray-300 text-xs font-bold shadow-sm"
            title="Jump to T+90h End"
          >
            ⏭
          </button>
        </div>

        {/* Forecast Timeline Slider */}
        <div className="flex-1 w-full flex items-center gap-3">
          <span className="text-xs font-bold text-blue-600 font-mono-code whitespace-nowrap min-w-[70px]">
            T+{selectedHour}h
          </span>
          <input
            type="range"
            min="0"
            max="89"
            value={selectedHour}
            onChange={(e) => setSelectedHour(parseInt(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
          />
          <span className="text-xs text-gray-500 font-mono-code whitespace-nowrap">T+90h</span>
        </div>

        {/* Current Time Display */}
        <div className="text-xs text-gray-500 font-mono-code whitespace-nowrap">
          Sim Time:{" "}
          <span className="text-gray-800 font-bold">
            {new Date(currentForecast.time).toLocaleDateString([], {
              month: "short",
              day: "numeric",
            })}{" "}
            {new Date(currentForecast.time).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}{" "}
            UTC
          </span>
        </div>
      </div>
    </div>
  );
}

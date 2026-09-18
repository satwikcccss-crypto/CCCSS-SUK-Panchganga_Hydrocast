"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ExternalLink, Activity, ShieldAlert, Waves, ArrowUpRight, ArrowDownRight, Globe, Zap, TrendingUp } from 'lucide-react';

export interface GaugeSensor {
  id: string;
  name: string;
  river: string;
  location: { lat: number; lng: number };
  markerColor?: string;
  dangerLevels: {
    alert: number;
    warning: number;
    danger: number;
    hfl?: number;
  };
}

export interface GaugeData {
  waterLevel: number;
  forecastLevel?: number;
  forecastTime?: string;
  alertLevel?: 'normal' | 'alert' | 'warning' | 'danger' | 'hfl_exceeded' | string;
  history?: Array<number | { timestamp: string; waterLevel: number }>;
}

export const getAlertConfig = (alertLevel: string) => {
  const lvl = alertLevel.toLowerCase();
  switch (lvl) {
    case 'hfl_exceeded':
    case 'extreme':
      return { label: 'HFL EXCEEDED', color: '#9333ea', bg: '#f3e8ff' };
    case 'danger':
      return { label: 'DANGER', color: '#ef4444', bg: '#fee2e2' };
    case 'warning':
      return { label: 'WARNING', color: '#f97316', bg: '#ffedd5' };
    case 'alert':
      return { label: 'ALERT', color: '#eab308', bg: '#fef9c3' };
    case 'normal':
    default:
      return { label: 'NORMAL', color: '#0284c7', bg: '#e0f2fe' };
  }
};

export const EngineeringGauge: React.FC<{
  sensor: GaugeSensor;
  data: GaugeData;
  onClick?: () => void;
  noHeader?: boolean;
}> = ({ sensor, data, onClick, noHeader = false }) => {
  const level = data?.waterLevel || 0;
  const forecastLevel = data?.forecastLevel;
  const alertConfig = getAlertConfig(data?.alertLevel || 'normal');
  const color = alertConfig.color;

  const H = 400, W = 204, TX = 62, TW = 78, PADT = 30, PADB = 22;
  const TR = TX + TW, UH = H - PADT - PADB;
  
  // Use a zoom range that covers both current level and forecast peak
  const maxRef = Math.max(level, forecastLevel ?? level, sensor.dangerLevels.alert - 1.0);
  const minRef = Math.min(level, forecastLevel ?? level);
  const ZM = Math.max(2.8, (maxRef - minRef) + 1.8);

  const lo = Math.min(minRef - 1.0, level - 2.0);
  const hi = lo + ZM * 2;

  const eY = (e: number) => PADT + UH * (1 - (e - lo) / (hi - lo));
  const wY = eY(level);
  const wH = H - PADB - wY;

  const fcY = forecastLevel !== undefined && forecastLevel <= hi && forecastLevel >= lo ? eY(forecastLevel) : null;
  const wnY = sensor.dangerLevels.warning <= hi && sensor.dangerLevels.warning >= lo ? eY(sensor.dangerLevels.warning) : null;
  const dnY = sensor.dangerLevels.danger <= hi && sensor.dangerLevels.danger >= lo ? eY(sensor.dangerLevels.danger) : null;
  const alY = sensor.dangerLevels.alert <= hi && sensor.dangerLevels.alert >= lo ? eY(sensor.dangerLevels.alert) : null;

  const bands: React.ReactNode[] = [];
  let b = Math.floor(lo * 2) / 2;
  while (b < hi + 0.01) {
    const y1 = eY(b + 0.5);
    const y2 = eY(b);
    const yTop = Math.max(PADT, Math.min(y1, y2));
    const yBot = Math.min(H - PADB, Math.max(y1, y2));
    if (yBot > yTop) {
      const i = Math.round(b * 2);
      if (i % 2 === 0) {
        bands.push(<rect key={b} x={TX} y={yTop.toFixed(1)} width={TW} height={(yBot - yTop).toFixed(1)} fill="rgba(0,0,0,0.03)" />);
      }
    }
    b = Math.round((b + 0.5) * 100) / 100;
  }

  const tks: React.ReactNode[] = [];
  let e = Math.ceil(lo * 10) / 10;
  while (e <= hi + 0.001) {
    const r = Math.round(e * 100) / 100;
    const y = eY(r);
    const fp = Math.abs(r - Math.round(r));
    const maj = fp < 0.005, mid = !maj && Math.abs(fp - 0.5) < 0.005;
    const tl = maj ? 13 : mid ? 8 : 3.5;
    const sw = maj ? 0.95 : mid ? 0.6 : 0.28;
    const sc = maj ? '#475569' : mid ? '#64748b' : '#94a3b8';

    tks.push(<line key={`l1_${r}`} x1={TX - tl} y1={y.toFixed(1)} x2={TX} y2={y.toFixed(1)} stroke={sc} strokeWidth={sw} />);
    tks.push(<line key={`l2_${r}`} x1={TR} y1={y.toFixed(1)} x2={TR + tl} y2={y.toFixed(1)} stroke={sc} strokeWidth={sw} />);

    if (maj) {
      tks.push(<text key={`t1_${r}`} x={TX - 17} y={(y + 3.5).toFixed(1)} textAnchor="end" fontSize="8.5" fontFamily="'JetBrains Mono', monospace" fill="#475569" fontWeight="bold">{Math.round(r)}</text>);
      tks.push(<line key={`l3_${r}`} x1={TX} y1={y.toFixed(1)} x2={TR} y2={y.toFixed(1)} stroke="rgba(0,0,0,0.05)" strokeWidth=".5" />);
    } else if (mid) {
      tks.push(<text key={`t2_${r}`} x={TX - 17} y={(y + 3).toFixed(1)} textAnchor="end" fontSize="7" fontFamily="'JetBrains Mono', monospace" fill="#64748b">.5</text>);
      tks.push(<line key={`l4_${r}`} x1={TX} y1={y.toFixed(1)} x2={TR} y2={y.toFixed(1)} stroke="rgba(0,0,0,0.05)" strokeWidth=".35" strokeDasharray="2,5" />);
    }
    e = Math.round((e + 0.1) * 100) / 100;
  }

  let wp = `M${TX - 240},${wY.toFixed(1)}`;
  for (let i = 0; i < 24; i++) wp += ` q20,${i % 2 === 0 ? -2.1 : 2.1} 40,0`;
  wp += ` V${H - PADB} H${TX - 240} Z`;

  const calcZoneHeight = (yBottom: number, yTop: number) => {
    const bottom = Math.min(Math.max(yBottom, PADT), H - PADB);
    const top = Math.min(Math.max(yTop, PADT), H - PADB);
    return { y: top, height: Math.max(0, bottom - top) };
  };

  const normZone = calcZoneHeight(H - PADB, eY(sensor.dangerLevels.warning));
  const warnZone = calcZoneHeight(eY(sensor.dangerLevels.warning), eY(sensor.dangerLevels.danger));
  const dangZone = calcZoneHeight(eY(sensor.dangerLevels.danger), PADT);
  const bY = Math.max(PADT + 18, Math.min(H - PADB - 6, wY));

  return (
    <div 
      className={`relative cursor-pointer group bg-white rounded-xl border border-slate-200 hover:border-blue-500 shadow-sm transition-all h-full flex flex-col ${noHeader ? 'border-none shadow-none bg-transparent' : 'p-4'}`}
      onClick={onClick}
    >
      {!noHeader && (
        <div className="flex items-center justify-between mb-3 flex-shrink-0">
          <div>
            <h4 className="text-xs font-bold text-slate-900 tracking-wider leading-tight">{sensor.name}</h4>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-[9px] font-bold text-slate-400 font-mono">MSL DATUM</span>
              {data.forecastLevel && (
                <span className="text-[9px] font-bold text-cyan-700 bg-cyan-50 px-1.5 py-0.2 rounded border border-cyan-200">
                  Peak: {data.forecastLevel.toFixed(2)}m
                </span>
              )}
            </div>
          </div>
          <div className="text-right">
            <div className="text-base font-black font-mono tracking-tighter" style={{ color: alertConfig.color }}>
              {level.toFixed(2)}m
            </div>
            <div className="text-[8px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded shadow-sm" style={{ backgroundColor: alertConfig.color, color: '#fff' }}>
              {alertConfig.label}
            </div>
          </div>
        </div>
      )}

      <div className="relative flex-grow min-h-[300px] w-full flex justify-center items-center">
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="100%" style={{ display: 'block', overflow: 'visible', maxHeight: '100%' }}>
          <defs>
            <clipPath id={`cpTube_${sensor.id}`}><rect x={TX} y={PADT} width={TW} height={UH} /></clipPath>
            <linearGradient id={`wgTube_${sensor.id}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity=".7" />
              <stop offset="100%" stopColor={color} stopOpacity=".3" />
            </linearGradient>
            <linearGradient id={`znNormal_${sensor.id}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#22c55e" stopOpacity=".15"/><stop offset="100%" stopColor="#86efac" stopOpacity=".05"/></linearGradient>
            <linearGradient id={`znAlert_${sensor.id}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#eab308" stopOpacity=".15"/><stop offset="100%" stopColor="#fde047" stopOpacity=".05"/></linearGradient>
            <linearGradient id={`znDanger_${sensor.id}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#ef4444" stopOpacity=".15"/><stop offset="100%" stopColor="#f87171" stopOpacity=".05"/></linearGradient>
          </defs>

          <text x={TX + TW / 2} y={PADT - 17} textAnchor="middle" fontSize="6.5" fontFamily="'JetBrains Mono', monospace" fill="#64748b" letterSpacing=".14em" fontWeight="bold">ELV · m MSL</text>
          <text x={TX + TW / 2} y={PADT - 5} textAnchor="middle" fontSize="6" fontFamily="'JetBrains Mono', monospace" fill="#94a3b8">▲{hi.toFixed(1)}</text>

          <g clipPath={`url(#cpTube_${sensor.id})`}>
            <rect x={TX} y={PADT} width={TW} height={UH} fill="#f8fafc" />
            <rect x={TX} y={normZone.y} width={TW} height={normZone.height} fill={`url(#znNormal_${sensor.id})`} />
            <rect x={TX} y={warnZone.y} width={TW} height={warnZone.height} fill={`url(#znAlert_${sensor.id})`} />
            <rect x={TX} y={dangZone.y} width={TW} height={dangZone.height} fill={`url(#znDanger_${sensor.id})`} />
            {bands}
          </g>

          {tks}

          <g clipPath={`url(#cpTube_${sensor.id})`}>
            <rect x={TX} y={wY.toFixed(1)} width={TW} height={wH.toFixed(1)} fill={`url(#wgTube_${sensor.id})`} />
            <path className="svg-water-wave" d={wp} fill={color} opacity=".5" />
          </g>

          {/* Alert Level Line */}
          {alY !== null && (
            <g>
              <line x1={TX} y1={alY.toFixed(1)} x2={TR} y2={alY.toFixed(1)} stroke="#eab308" strokeWidth="1.2" strokeDasharray="4,2" />
              <text x={TR + 3} y={(alY + 3).toFixed(1)} fontSize="6" fontFamily="'JetBrains Mono', monospace" fill="#eab308" fontWeight="bold">ALT {sensor.dangerLevels.alert.toFixed(1)}m</text>
            </g>
          )}

          {/* Warning Level Line */}
          {wnY !== null && (
            <g>
              <line x1={TX} y1={wnY.toFixed(1)} x2={TR} y2={wnY.toFixed(1)} stroke="#f97316" strokeWidth="1.5" strokeDasharray="6,3" />
              <text x={TR + 3} y={(wnY + 3).toFixed(1)} fontSize="6.5" fontFamily="'JetBrains Mono', monospace" fill="#f97316" fontWeight="bold">WRN {sensor.dangerLevels.warning.toFixed(2)}m</text>
            </g>
          )}

          {/* Danger Level Line */}
          {dnY !== null && (
            <g>
              <line x1={TX} y1={dnY.toFixed(1)} x2={TR} y2={dnY.toFixed(1)} stroke="#ef4444" strokeWidth="1.5" strokeDasharray="3,2" />
              <text x={TR + 3} y={(dnY + 3).toFixed(1)} fontSize="6.5" fontFamily="'JetBrains Mono', monospace" fill="#ef4444" fontWeight="bold">DNG {sensor.dangerLevels.danger.toFixed(1)}m</text>
            </g>
          )}

          {/* Forecast Peak Stage Marker */}
          {fcY !== null && (
            <g>
              <line x1={TX} y1={fcY.toFixed(1)} x2={TR} y2={fcY.toFixed(1)} stroke="#0891b2" strokeWidth="2" strokeDasharray="3,2" />
              <polygon points={`${TX - 2},${fcY.toFixed(1)} ${TX - 9},${(fcY - 4).toFixed(1)} ${TX - 9},${(fcY + 4).toFixed(1)}`} fill="#0891b2" />
              <rect x={TX - 54} y={(fcY - 7).toFixed(1)} width="43" height="14" rx="2" fill="#0891b2" />
              <text x={TX - 33} y={(fcY + 3).toFixed(1)} textAnchor="middle" fontSize="6.5" fontFamily="'JetBrains Mono', monospace" fontWeight="bold" fill="#ffffff">FCST {forecastLevel?.toFixed(2)}m</text>
            </g>
          )}

          <rect x={TX} y={PADT} width="3" height={UH} fill="#fff" opacity=".3" clipPath={`url(#cpTube_${sensor.id})`} />
          <rect x={TX} y={PADT} width={TW} height={UH} fill="none" stroke="#cbd5e1" strokeWidth="1.5" rx="1" />

          {/* Current Level Badge */}
          <rect x={TX + 2} y={(bY - 17).toFixed(1)} width="62" height="18" rx="2" fill="#ffffff" stroke={color} strokeWidth="1.5" />
          <text x={TX + 33} y={(bY - 4.5).toFixed(1)} textAnchor="middle" fontSize="9.5" fontFamily="'JetBrains Mono', monospace" fontWeight="bold" fill={color} letterSpacing=".05em">{level.toFixed(2)} m</text>

          <line x1={TX} y1={wY.toFixed(1)} x2={TR} y2={wY.toFixed(1)} stroke="rgba(255,255,255,.5)" strokeWidth="1.5" clipPath={`url(#cpTube_${sensor.id})`} />
          <polygon points={`${TX - 3},${wY.toFixed(1)} ${TX - 14},${(wY - 5.5).toFixed(1)} ${TX - 14},${(wY + 5.5).toFixed(1)}`} fill={color} />
          <polygon points={`${TR + 3},${wY.toFixed(1)} ${TR + 14},${(wY - 5.5).toFixed(1)} ${TR + 14},${(wY + 5.5).toFixed(1)}`} fill={color} />

          <text x={TX + TW / 2} y={H - 4} textAnchor="middle" fontSize="6" fontFamily="'JetBrains Mono', monospace" fill="#94a3b8">▼{lo.toFixed(1)}</text>
        </svg>
      </div>
    </div>
  );
};

// Simplified Dashboard Indicator Card
export const SimpleIndicator: React.FC<{
  sensor: GaugeSensor;
  data: GaugeData;
  onClick?: () => void;
  active?: boolean;
}> = ({ sensor, data, onClick, active }) => {
  const level = data?.waterLevel || 0;
  const alertConfig = getAlertConfig(data?.alertLevel || 'normal');
  const history = data?.history || [];
  const prevLevel = history.length > 5 ? (typeof history[history.length - 6] === 'object' ? (history[history.length - 6] as any).waterLevel : history[history.length - 6]) : level;
  const isRising = level >= prevLevel;

  return (
    <motion.div 
      whileHover={{ y: -4 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className={`bg-white rounded-xl p-4 cursor-pointer relative overflow-hidden transition-all border shadow-sm border-l-4 ${
        active ? 'ring-2 ring-blue-600 bg-blue-50/50' : 'hover:border-blue-400'
      }`}
      style={{ borderLeftColor: alertConfig.color }}
    >
      <div className="flex justify-between items-start mb-2">
        <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest leading-tight">{sensor.name}</h4>
        <div className={`p-1 rounded-md ${active ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-400'}`}>
          <Waves className="w-3 h-3" />
        </div>
      </div>

      <div className="flex items-baseline gap-1.5">
        <span className="text-2xl font-mono font-black text-slate-800 tracking-tighter">{level.toFixed(2)}</span>
        <span className="text-[9px] font-bold text-slate-400 uppercase">m</span>
      </div>

      <div className="mt-2 flex items-center justify-between">
        <div className="flex items-center gap-1">
          {isRising ? <ArrowUpRight className="w-3 h-3 text-emerald-500" /> : <ArrowDownRight className="w-3 h-3 text-red-500" />}
          <span className={`text-[8px] font-bold uppercase tracking-widest ${isRising ? 'text-emerald-600' : 'text-red-500'}`}>
            {isRising ? 'Rising' : 'Falling'}
          </span>
        </div>
        <span className="text-[8px] font-bold text-slate-400 font-mono">MSL</span>
      </div>
    </motion.div>
  );
};



export default EngineeringGauge;

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
  const alertConfig = getAlertConfig(data?.alertLevel || 'normal');
  const color = alertConfig.color;

  const H = 400, W = 204, TX = 62, TW = 78, PADT = 30, PADB = 22;
  const TR = TX + TW, UH = H - PADT - PADB, ZM = 2.4;

  const lo = level - ZM;
  const hi = level + ZM;

  const eY = (e: number) => PADT + UH * (1 - (e - lo) / (hi - lo));
  const wY = eY(level);
  const wH = H - PADB - wY;

  const wnY = sensor.dangerLevels.warning <= hi && sensor.dangerLevels.warning >= lo ? eY(sensor.dangerLevels.warning) : null;
  const dnY = sensor.dangerLevels.danger <= hi && sensor.dangerLevels.danger >= lo ? eY(sensor.dangerLevels.danger) : null;
  
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
        <div className="flex items-center justify-between mb-4 flex-shrink-0">
          <div>
            <h4 className="text-xs font-bold text-slate-900 tracking-wider leading-tight">{sensor.name}</h4>
            <span className="text-[9px] font-bold text-slate-400 font-mono">PNCHGN-RTDAS-RWL-{sensor.id.toUpperCase()}</span>
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

          {wnY !== null && (
            <g>
              <line x1={TX} y1={wnY.toFixed(1)} x2={TR} y2={wnY.toFixed(1)} stroke="#f97316" strokeWidth="1.5" strokeDasharray="6,3" />
              <line x1={TR} y1={wnY.toFixed(1)} x2={TR + 15} y2={wnY.toFixed(1)} stroke="#f97316" strokeWidth="1.5" strokeDasharray="6,3" />
              <text x={TR + 3} y={(wnY + 3.5).toFixed(1)} fontSize="6.5" fontFamily="'JetBrains Mono', monospace" fill="#f97316" fontWeight="bold" letterSpacing=".08em">WRN</text>
            </g>
          )}
          {dnY !== null && (
            <g>
              <line x1={TX} y1={dnY.toFixed(1)} x2={TR} y2={dnY.toFixed(1)} stroke="#ef4444" strokeWidth="1.5" strokeDasharray="3,2" />
              <line x1={TR} y1={dnY.toFixed(1)} x2={TR + 15} y2={dnY.toFixed(1)} stroke="#ef4444" strokeWidth="1.5" strokeDasharray="3,2" />
              <text x={TR + 3} y={(dnY + 3.5).toFixed(1)} fontSize="6.5" fontFamily="'JetBrains Mono', monospace" fill="#ef4444" fontWeight="bold" letterSpacing=".08em">DNG</text>
            </g>
          )}

          <rect x={TX} y={PADT} width="3" height={UH} fill="#fff" opacity=".3" clipPath={`url(#cpTube_${sensor.id})`} />
          <rect x={TX} y={PADT} width={TW} height={UH} fill="none" stroke="#cbd5e1" strokeWidth="1.5" rx="1" />

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

// MiniTrend SVG sparkline
export const MiniTrend: React.FC<{ history: Array<number | { waterLevel: number }> }> = ({ history }) => {
  if (!history || history.length < 2) return <div className="h-full flex items-center justify-center text-[10px] text-slate-400 font-bold uppercase tracking-widest">Calibrating Stream...</div>;
  
  const values = history.map(h => typeof h === 'object' ? h.waterLevel : h);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = (max - min) || 0.1;
  const width = 300;
  const height = 60;
  
  const points = values.map((val, i) => {
    const x = (i / (values.length - 1)) * width;
    const y = height - ((val - min) / range) * height;
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      <polyline fill="none" stroke="#38bdf8" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" points={points} />
      <circle cx={(values.length - 1) / (values.length - 1) * width} cy={height - ((values[values.length-1] - min) / range) * height} r="3" fill="#38bdf8" />
    </svg>
  );
};

// Modal popup showing full detailed analytics and zoom gauge
export const ZoomedGauge: React.FC<{
  sensor: GaugeSensor;
  data: GaugeData;
  onClose: () => void;
}> = ({ sensor, data, onClose }) => {
  const history = data?.history || [];
  const current = data?.waterLevel || 0;
  
  const getChange = (pts: number) => {
    if (!history || history.length < pts) return "0.0";
    const pastEntry = history[history.length - pts];
    const pastValue = typeof pastEntry === 'object' ? pastEntry.waterLevel : pastEntry;
    if (pastValue === undefined || pastValue === null) return "0.0";
    const diff = (current - pastValue);
    return isNaN(diff) ? "0.0" : diff.toFixed(2);
  };

  const stats = [
    { label: 'Current 1h', val: getChange(6), color: 'text-blue-600', icon: <Activity className="w-3 h-3" /> },
    { label: 'Rolling 3h', val: getChange(18), color: 'text-emerald-600', icon: <TrendingUp className="w-3 h-3" /> },
    { label: 'Rolling 6h', val: getChange(36), color: 'text-amber-600', icon: <Waves className="w-3 h-3" /> },
    { label: 'Rolling 12h', val: getChange(72), color: 'text-orange-600', icon: <ShieldAlert className="w-3 h-3" /> },
    { label: 'Rolling 24h', val: getChange(144), color: 'text-rose-600', icon: <Zap className="w-3 h-3" /> }
  ];

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[200] flex items-center justify-center p-4">
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0 bg-slate-900/60 backdrop-blur-md" onClick={onClose} />
        
        <motion.div 
          initial={{ scale: 0.95, opacity: 0, y: 20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.95, opacity: 0, y: 20 }}
          className="bg-white rounded-[2rem] relative z-10 w-full max-w-6xl shadow-2xl flex flex-col md:flex-row overflow-y-auto md:overflow-hidden max-h-[95vh] border border-white/20"
        >
          {/* LEFT SIDEBAR (Station Profile) */}
          <div className="w-full md:w-[340px] bg-slate-50/70 border-b md:border-b-0 md:border-r border-slate-200 p-6 flex flex-col shrink-0 md:overflow-y-auto">
            <div className="flex items-center gap-3 mb-6">
                <div className="w-9 h-9 rounded-xl bg-blue-700 flex items-center justify-center shadow-lg shadow-blue-700/20">
                    <Zap className="w-5 h-5 text-white" />
                </div>
                <div>
                    <h4 className="text-[9px] font-black text-blue-900 uppercase tracking-widest leading-none">CCCSS, Shivaji University</h4>
                    <span className="text-[8px] font-bold text-slate-400 uppercase tracking-widest mt-1 block">Institutional RTDAS Control</span>
                </div>
            </div>

            <div className="mb-6">
                <div className="inline-block px-2 py-0.5 bg-slate-100 rounded text-[9px] font-mono font-bold text-slate-500 mb-2 border border-slate-200">
                    RWL-{sensor.id.toUpperCase()} • RTDAS
                </div>
                <h2 className="text-xl font-black text-slate-800 tracking-tight uppercase leading-tight">
                    {sensor.name} STATION:<br/>
                    <span className="text-amber-600 italic opacity-80 text-sm">{sensor.river} Monitoring</span>
                </h2>
                <div className="flex items-center gap-2 mt-3 text-[9px] font-bold text-slate-400">
                    <Globe className="w-3 h-3" />
                    <span>STN COORDS: {sensor.location.lat.toFixed(4)}°N, {sensor.location.lng.toFixed(4)}°E</span>
                </div>
            </div>

            {/* INTEGRATED GAUGE (Left) */}
            <div className="flex-grow flex flex-col items-center justify-center py-4 bg-white rounded-2xl border border-slate-200 shadow-inner min-h-[350px]">
                <h4 className="text-[8px] font-bold text-slate-400 uppercase tracking-[0.2em] mb-4">Water Level Gauge MSL</h4>
                <div className="w-full max-h-[400px]">
                    <EngineeringGauge sensor={sensor} data={data} noHeader={true} />
                </div>
            </div>
            
            <div className="mt-6 pt-4 border-t border-slate-200">
               <p className="text-[9px] text-slate-500 italic leading-relaxed">
                  Field telemetry is captured via radar ultrasonic sensors and transmitted in real-time. Data is research-grade from the CCCSS flood network.
               </p>
            </div>
          </div>

          {/* RIGHT DASHBOARD (Analytics) */}
          <div className="flex-grow p-6 flex flex-col bg-white md:overflow-hidden relative">
            <button onClick={onClose} className="absolute top-6 right-6 z-20 p-2 text-slate-400 hover:text-red-500 rounded-full transition-all hover:bg-slate-50 box-content">
              <X className="w-6 h-6" />
            </button>

            {/* ANALYTICS HEADER */}
            <div className="flex items-center gap-1 mb-6 bg-slate-50 p-1 rounded-xl self-start">
               <div className="px-4 py-2 text-[10px] font-bold uppercase tracking-wider rounded-lg bg-white text-blue-700 shadow-sm ring-1 ring-slate-200">
                 View Analytics
               </div>
            </div>

            <div className="flex-grow overflow-y-auto pr-1">
                <div className="space-y-6">
                  {/* Rolling Stats Header */}
                  <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
                       {stats.map(s => (
                          <div key={s.label} className="bg-white border border-slate-200 rounded-xl p-3 px-4 transition-all hover:border-blue-400 shadow-sm relative overflow-hidden group">
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">{s.label}</span>
                                <div className={`${s.color} opacity-40 group-hover:opacity-100 transition-opacity`}>{s.icon}</div>
                              </div>
                              <div className={`text-lg font-mono font-black ${s.color} flex items-baseline gap-1`}>
                                  {parseFloat(s.val) > 0 ? '+' : ''}{s.val}
                                  <span className="text-[9px] font-bold opacity-60">m</span>
                              </div>
                          </div>
                       ))}
                  </div>

                  {/* MINI HYETOGRAPH CHART */}
                  <div className="p-4 md:p-5 bg-white border border-slate-200 rounded-[1.5rem] shadow-sm relative overflow-hidden h-[300px] flex flex-col">
                      <div className="flex items-center justify-between mb-4">
                          <div className="flex items-center gap-2">
                              <div className="w-2 h-2 rounded-full bg-blue-600 animate-pulse" />
                              <h4 className="text-[10px] font-black text-slate-700 uppercase tracking-widest leading-none">WSL Water Surface Elevation Trend</h4>
                          </div>
                          <div className="flex items-center gap-2">
                             <div className="text-[8px] font-bold text-slate-400 uppercase tracking-widest px-2 py-0.5 bg-slate-50 rounded border border-slate-200">Live Telemetry</div>
                          </div>
                      </div>
                      <div className="flex-grow">
                          <MiniTrend history={history} />
                      </div>
                  </div>
                </div>
            </div>

          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default EngineeringGauge;

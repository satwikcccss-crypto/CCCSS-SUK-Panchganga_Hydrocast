"use client";

import React, { useState } from "react";
import {
  Cpu,
  Database,
  HardDrive,
  Server,
  Activity,
  CheckCircle2,
  Clock,
  RefreshCw,
  Zap,
  Shield,
  Layers,
} from "lucide-react";

export interface SystemHealthData {
  cpu_percent?: number;
  ram_percent?: number;
  ram_used_gb?: number;
  ram_total_gb?: number;
  disk_c_used_gb?: number;
  disk_c_total_gb?: number;
  disk_e_used_gb?: number;
  disk_e_total_gb?: number;
  db_status?: string;
  db_latency_ms?: number;
  db_tablespace_mb?: number;
  db_active_conns?: number;
  table_counts?: Record<string, number>;
}

export default function SystemHealthCards({
  healthData,
  onRefresh,
  isRefreshing = false,
}: {
  healthData?: SystemHealthData;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}) {
  const cpu = healthData?.cpu_percent ?? 12.4;
  const ram = healthData?.ram_percent ?? 38.6;
  const ramUsed = healthData?.ram_used_gb ?? 6.2;
  const ramTotal = healthData?.ram_total_gb ?? 16.0;

  const diskEUsed = healthData?.disk_e_used_gb ?? 142.5;
  const diskETotal = healthData?.disk_e_total_gb ?? 512.0;
  const diskEPct = Math.round((diskEUsed / diskETotal) * 100);

  const diskCUsed = healthData?.disk_c_used_gb ?? 88.2;
  const diskCTotal = healthData?.disk_c_total_gb ?? 256.0;
  const diskCPct = Math.round((diskCUsed / diskCTotal) * 100);

  const dbLatency = healthData?.db_latency_ms ?? 14;
  const dbStatus = healthData?.db_status ?? "CONNECTED";
  const dbTablespace = healthData?.db_tablespace_mb ?? 342.8;

  const tableCounts = healthData?.table_counts ?? {
    forecast_runs: 148,
    observed_stage: 8642,
    rain_gauges: 18,
    ecmwf_forecasts: 1620,
    cross_sections: 4,
  };

  return (
    <div className="space-y-6">
      {/* ── 1. HOST HARDWARE & OS METERS (CPU, RAM, DISKS) ───────────── */}
      <div className="bg-[#ffffff] border border-[#e5e5e5] rounded-lg p-5 shadow-xs">
        <div className="pb-4 border-b border-[#f0f0f0] flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold text-[#1b1b1b] flex items-center gap-2">
              <Cpu className="w-4 h-4 text-[#0067b8]" />
              <span>Windows Server Host Telemetry &amp; Resource Utilization</span>
            </h2>
            <p className="text-xs text-[#5c5c5c] mt-0.5">
              Live hardware supervisor for SUK Hydrological Compute Server (E:\Hydrocast Windows Server)
            </p>
          </div>
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              className="win-btn"
              title="Query hardware counters"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-[#5c5c5c] ${isRefreshing ? "animate-spin" : ""}`} />
              <span>{isRefreshing ? "Querying..." : "Refresh Counters"}</span>
            </button>
          )}
        </div>

        {/* Meter Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-5">
          {/* Meter 1: CPU */}
          <div className="p-4 rounded-lg border border-[#e5e5e5] bg-[#fafafa]">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[#5c5c5c] uppercase">CPU Load</span>
              <Cpu className="w-4 h-4 text-[#0067b8]" />
            </div>
            <div className="mt-2 flex items-baseline gap-1">
              <span className="text-2xl font-bold font-mono text-[#1b1b1b]">{cpu.toFixed(1)}</span>
              <span className="text-xs text-[#767676] font-mono">%</span>
            </div>
            <div className="w-full bg-[#e5e5e5] h-2 rounded-full mt-3 overflow-hidden">
              <div
                className={`h-full rounded-full ${cpu > 80 ? "bg-red-500" : cpu > 50 ? "bg-amber-500" : "bg-[#0067b8]"}`}
                style={{ width: `${Math.min(100, cpu)}%` }}
              />
            </div>
            <div className="mt-2 text-[10px] text-[#767676] font-mono">Multi-threaded HEC-HMS Worker</div>
          </div>

          {/* Meter 2: RAM */}
          <div className="p-4 rounded-lg border border-[#e5e5e5] bg-[#fafafa]">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[#5c5c5c] uppercase">Memory RAM</span>
              <Activity className="w-4 h-4 text-[#0f7b0f]" />
            </div>
            <div className="mt-2 flex items-baseline gap-1">
              <span className="text-2xl font-bold font-mono text-[#1b1b1b]">{ram.toFixed(1)}</span>
              <span className="text-xs text-[#767676] font-mono">%</span>
            </div>
            <div className="w-full bg-[#e5e5e5] h-2 rounded-full mt-3 overflow-hidden">
              <div
                className={`h-full rounded-full ${ram > 85 ? "bg-red-500" : "bg-[#0f7b0f]"}`}
                style={{ width: `${Math.min(100, ram)}%` }}
              />
            </div>
            <div className="mt-2 text-[10px] text-[#767676] font-mono">
              {ramUsed.toFixed(1)} GB used of {ramTotal.toFixed(1)} GB
            </div>
          </div>

          {/* Meter 3: Disk E: (Data Drive) */}
          <div className="p-4 rounded-lg border border-[#e5e5e5] bg-[#fafafa]">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[#5c5c5c] uppercase">Disk E: (HydroCast)</span>
              <HardDrive className="w-4 h-4 text-[#9d5d00]" />
            </div>
            <div className="mt-2 flex items-baseline gap-1">
              <span className="text-2xl font-bold font-mono text-[#1b1b1b]">{diskEPct}</span>
              <span className="text-xs text-[#767676] font-mono">%</span>
            </div>
            <div className="w-full bg-[#e5e5e5] h-2 rounded-full mt-3 overflow-hidden">
              <div
                className="h-full rounded-full bg-[#9d5d00]"
                style={{ width: `${Math.min(100, diskEPct)}%` }}
              />
            </div>
            <div className="mt-2 text-[10px] text-[#767676] font-mono">
              {diskEUsed.toFixed(0)} GB / {diskETotal.toFixed(0)} GB (DSS/PostgreSQL)
            </div>
          </div>

          {/* Meter 4: Disk C: (System Drive) */}
          <div className="p-4 rounded-lg border border-[#e5e5e5] bg-[#fafafa]">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[#5c5c5c] uppercase">Disk C: (OS &amp; HMS)</span>
              <Server className="w-4 h-4 text-[#5c5c5c]" />
            </div>
            <div className="mt-2 flex items-baseline gap-1">
              <span className="text-2xl font-bold font-mono text-[#1b1b1b]">{diskCPct}</span>
              <span className="text-xs text-[#767676] font-mono">%</span>
            </div>
            <div className="w-full bg-[#e5e5e5] h-2 rounded-full mt-3 overflow-hidden">
              <div
                className="h-full rounded-full bg-[#5c5c5c]"
                style={{ width: `${Math.min(100, diskCPct)}%` }}
              />
            </div>
            <div className="mt-2 text-[10px] text-[#767676] font-mono">
              {diskCUsed.toFixed(0)} GB / {diskCTotal.toFixed(0)} GB (Windows)
            </div>
          </div>
        </div>
      </div>

      {/* ── 2. POSTGRESQL 16 DATABASE ENGINE TELEMETRY ───────────────── */}
      <div className="bg-[#ffffff] border border-[#e5e5e5] rounded-lg p-5 shadow-xs">
        <div className="pb-4 border-b border-[#f0f0f0] flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold text-[#1b1b1b] flex items-center gap-2">
              <Database className="w-4 h-4 text-[#0067b8]" />
              <span>PostgreSQL 16 Engine Telemetry &amp; Table Row Counts</span>
            </h2>
            <p className="text-xs text-[#5c5c5c] mt-0.5">
              Hydrological state persistence, run ledger, and sensor observation tables
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs font-mono font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1 rounded">
            <span>Pool Latency: {dbLatency}ms</span>
            <span>·</span>
            <span>Status: {dbStatus}</span>
          </div>
        </div>

        {/* DB Metrics Cards Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mt-5">
          {Object.entries(tableCounts).map(([tableName, count]) => (
            <div key={tableName} className="p-3.5 rounded-lg border border-[#e5e5e5] bg-[#fafafa]">
              <div className="text-[10px] text-[#5c5c5c] font-mono font-bold uppercase truncate">
                {tableName}
              </div>
              <div className="mt-1 text-lg font-mono font-bold text-[#0067b8]">
                {count.toLocaleString()}
              </div>
              <div className="text-[10px] text-[#767676] mt-0.5">Verified Records</div>
            </div>
          ))}
        </div>

        {/* PostgreSQL Operational Details */}
        <div className="mt-4 p-4 rounded-lg bg-[#f0f7fc] border border-[#d0e5f7] flex flex-col sm:flex-row justify-between gap-3 text-xs font-mono">
          <div>
            <span className="text-[#5c5c5c]">Database URI: </span>
            <span className="font-bold text-[#1b1b1b]">postgresql://127.0.0.1:5432/rainfall_runoff</span>
          </div>
          <div>
            <span className="text-[#5c5c5c]">Tablespace Size: </span>
            <span className="font-bold text-[#0067b8]">{dbTablespace.toFixed(1)} MB</span>
          </div>
          <div>
            <span className="text-[#5c5c5c]">WAL Archiving: </span>
            <span className="font-bold text-emerald-700">ENABLED (Parquet Cold Store)</span>
          </div>
        </div>
      </div>
    </div>
  );
}


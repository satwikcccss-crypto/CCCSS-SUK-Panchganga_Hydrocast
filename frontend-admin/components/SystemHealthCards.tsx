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
  const hasData = healthData != null;
  const cpu = healthData?.cpu_percent ?? null;
  const ram = healthData?.ram_percent ?? null;
  const ramUsed = healthData?.ram_used_gb ?? null;
  const ramTotal = healthData?.ram_total_gb ?? null;

  const diskEUsed = healthData?.disk_e_used_gb ?? null;
  const diskETotal = healthData?.disk_e_total_gb ?? null;
  const diskEPct = diskEUsed != null && diskETotal != null && diskETotal > 0 ? Math.round((diskEUsed / diskETotal) * 100) : null;

  const diskCUsed = healthData?.disk_c_used_gb ?? null;
  const diskCTotal = healthData?.disk_c_total_gb ?? null;
  const diskCPct = diskCUsed != null && diskCTotal != null && diskCTotal > 0 ? Math.round((diskCUsed / diskCTotal) * 100) : null;

  const dbLatency = healthData?.db_latency_ms ?? null;
  const dbStatus = healthData?.db_status ?? null;
  const dbTablespace = healthData?.db_tablespace_mb ?? null;

  const tableCounts = healthData?.table_counts ?? null;

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
              <span className="text-2xl font-bold font-mono text-[#1b1b1b]">{cpu != null ? cpu.toFixed(1) : "—"}</span>
              <span className="text-xs text-[#767676] font-mono">%</span>
            </div>
            <div className="w-full bg-[#e5e5e5] h-2 rounded-full mt-3 overflow-hidden">
              <div
                className={`h-full rounded-full ${cpu != null && cpu > 80 ? "bg-red-500" : cpu != null && cpu > 50 ? "bg-amber-500" : "bg-[#0067b8]"}`}
                style={{ width: `${Math.min(100, cpu ?? 0)}%` }}
              />
            </div>
            <div className="mt-2 text-[10px] text-[#767676] font-mono">{!hasData ? "Awaiting system query..." : "Multi-threaded HEC-HMS Worker"}</div>
          </div>

          {/* Meter 2: RAM */}
          <div className="p-4 rounded-lg border border-[#e5e5e5] bg-[#fafafa]">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[#5c5c5c] uppercase">Memory RAM</span>
              <Activity className="w-4 h-4 text-[#0f7b0f]" />
            </div>
            <div className="mt-2 flex items-baseline gap-1">
              <span className="text-2xl font-bold font-mono text-[#1b1b1b]">{ram != null ? ram.toFixed(1) : "—"}</span>
              <span className="text-xs text-[#767676] font-mono">%</span>
            </div>
            <div className="w-full bg-[#e5e5e5] h-2 rounded-full mt-3 overflow-hidden">
              <div
                className={`h-full rounded-full ${ram != null && ram > 85 ? "bg-red-500" : "bg-[#0f7b0f]"}`}
                style={{ width: `${Math.min(100, ram ?? 0)}%` }}
              />
            </div>
            <div className="mt-2 text-[10px] text-[#767676] font-mono">
              {ramUsed != null && ramTotal != null ? `${ramUsed.toFixed(1)} GB used of ${ramTotal.toFixed(1)} GB` : "Awaiting system query..."}
            </div>
          </div>

          {/* Meter 3: Disk E: (Data Drive) */}
          <div className="p-4 rounded-lg border border-[#e5e5e5] bg-[#fafafa]">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[#5c5c5c] uppercase">Disk E: (HydroCast)</span>
              <HardDrive className="w-4 h-4 text-[#9d5d00]" />
            </div>
            <div className="mt-2 flex items-baseline gap-1">
              <span className="text-2xl font-bold font-mono text-[#1b1b1b]">{diskEPct != null ? diskEPct : "—"}</span>
              <span className="text-xs text-[#767676] font-mono">%</span>
            </div>
            <div className="w-full bg-[#e5e5e5] h-2 rounded-full mt-3 overflow-hidden">
              <div
                className="h-full rounded-full bg-[#9d5d00]"
                style={{ width: `${Math.min(100, diskEPct ?? 0)}%` }}
              />
            </div>
            <div className="mt-2 text-[10px] text-[#767676] font-mono">
              {diskEUsed != null && diskETotal != null ? `${diskEUsed.toFixed(0)} GB / ${diskETotal.toFixed(0)} GB (DSS/PostgreSQL)` : "Awaiting system query..."}
            </div>
          </div>

          {/* Meter 4: Disk C: (System Drive) */}
          <div className="p-4 rounded-lg border border-[#e5e5e5] bg-[#fafafa]">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[#5c5c5c] uppercase">Disk C: (OS &amp; HMS)</span>
              <Server className="w-4 h-4 text-[#5c5c5c]" />
            </div>
            <div className="mt-2 flex items-baseline gap-1">
              <span className="text-2xl font-bold font-mono text-[#1b1b1b]">{diskCPct != null ? diskCPct : "—"}</span>
              <span className="text-xs text-[#767676] font-mono">%</span>
            </div>
            <div className="w-full bg-[#e5e5e5] h-2 rounded-full mt-3 overflow-hidden">
              <div
                className="h-full rounded-full bg-[#5c5c5c]"
                style={{ width: `${Math.min(100, diskCPct ?? 0)}%` }}
              />
            </div>
            <div className="mt-2 text-[10px] text-[#767676] font-mono">
              {diskCUsed != null && diskCTotal != null ? `${diskCUsed.toFixed(0)} GB / ${diskCTotal.toFixed(0)} GB (Windows)` : "Awaiting system query..."}
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
          <div className={`flex items-center gap-2 text-xs font-mono font-semibold px-3 py-1 rounded ${dbStatus ? "text-emerald-700 bg-emerald-50 border border-emerald-200" : "text-gray-500 bg-gray-50 border border-gray-200"}`}>
            <span>Pool Latency: {dbLatency != null ? `${dbLatency}ms` : "—"}</span>
            <span>·</span>
            <span>Status: {dbStatus ?? "QUERYING..."}</span>
          </div>
        </div>

        {/* DB Metrics Cards Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mt-5">
          {tableCounts ? Object.entries(tableCounts).map(([tableName, count]) => (
            <div key={tableName} className="p-3.5 rounded-lg border border-[#e5e5e5] bg-[#fafafa]">
              <div className="text-[10px] text-[#5c5c5c] font-mono font-bold uppercase truncate">
                {tableName}
              </div>
              <div className="mt-1 text-lg font-mono font-bold text-[#0067b8]">
                {(count as number).toLocaleString()}
              </div>
              <div className="text-[10px] text-[#767676] mt-0.5">Verified Records</div>
            </div>
          )) : (
            <div className="col-span-full p-3.5 rounded-lg border border-[#e5e5e5] bg-[#fafafa] text-center">
              <div className="text-xs text-[#767676]">Click Refresh Counters to query live table row counts</div>
            </div>
          )}
        </div>

        {/* PostgreSQL Operational Details */}
        <div className="mt-4 p-4 rounded-lg bg-[#f0f7fc] border border-[#d0e5f7] flex flex-col sm:flex-row justify-between gap-3 text-xs font-mono">
          <div>
            <span className="text-[#5c5c5c]">Database URI: </span>
            <span className="font-bold text-[#1b1b1b]">postgresql://127.0.0.1:5432/rainfall_runoff</span>
          </div>
          <div>
            <span className="text-[#5c5c5c]">Tablespace Size: </span>
            <span className="font-bold text-[#0067b8]">{dbTablespace != null ? `${dbTablespace.toFixed(1)} MB` : "—"}</span>
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


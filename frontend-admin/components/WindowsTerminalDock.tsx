"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Terminal,
  Maximize2,
  Minimize2,
  X,
  Copy,
  Trash2,
  Play,
  RotateCcw,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Layers,
  ChevronUp,
  ChevronDown,
} from "lucide-react";

export interface LogEntry {
  t?: string;
  timestamp?: string;
  lv?: string;
  level?: string;
  msg?: string;
  message?: string;
}

export interface PipelineStep {
  step: number;
  name: string;
  script?: string;
  status: "idle" | "running" | "success" | "failed" | "completed";
  duration_s?: number;
  details?: string;
}

const DEFAULT_STEPS: PipelineStep[] = [
  { step: 1, name: "Open-Meteo IFS 90h NWP Ingestion", script: "01_ingest_openmeteo.py", status: "completed", duration_s: 3.2, details: "18 Panchganga stations grid sync" },
  { step: 2, name: "ThingSpeak Ultrasonic Radar Ingestion", script: "02_ingest_thingspeak.py", status: "completed", duration_s: 1.1, details: "Shivaji Bridge channel 3424513" },
  { step: 3, name: "WRD River Telemetry Sync & QC", script: "03_ingest_wrd.py", status: "completed", duration_s: 1.4, details: "Quality control & anomaly validation" },
  { step: 4, name: "Dynamic Governing Station Evaluation", script: "04_eval_governing_stations.py", status: "completed", duration_s: 0.8, details: "Thiessen polygon weights S1-S9" },
  { step: 5, name: "HEC-DSS Meteorological Store Generation", script: "05_generate_dss.py", status: "completed", duration_s: 2.5, details: "Hourly precipitation hyetographs" },
  { step: 6, name: "Headless HEC-HMS 4.13 Basin Verification", script: "06_run_hec_hms.py", status: "completed", duration_s: 1.8, details: "Loss & transform parameter verification" },
  { step: 7, name: "Hydrological Routing Engine Execution", script: "07_hydrologic_routing.py", status: "completed", duration_s: 8.4, details: "Muskingum-Cunge channel & SCS-CN routing" },
  { step: 8, name: "Sink Node Hydrograph & Volume Extraction", script: "08_extract_hydrograph.py", status: "completed", duration_s: 1.2, details: "J_Outlet discharge & volume extraction" },
  { step: 9, name: "PCHIP Monotonic Stage Rating Conversion", script: "09_stage_conversion.py", status: "completed", duration_s: 0.9, details: "Shivaji Bridge & Rajaram Weir stages" },
  { step: 10, name: "PostgreSQL Time-Series Persistence", script: "10_persist_postgres.py", status: "completed", duration_s: 4.2, details: "Forecast series & run ledger write" },
  { step: 11, name: "CWC Flood Threshold Classification & Bulletins", script: "11_eval_alerts.py", status: "completed", duration_s: 1.6, details: "Alert, Warning, Danger thresholds" },
  { step: 12, name: "Real-Time Telemetry Validation & Broadcast", script: "12_broadcast_telemetry.py", status: "completed", duration_s: 2.1, details: "State persistence & WebSocket broadcast" },
];

export default function WindowsTerminalDock({
  isOpen,
  onClose,
  logs = [],
  pipeline,
  onTriggerRun,
  isRunning = false,
}: {
  isOpen: boolean;
  onClose: () => void;
  logs?: LogEntry[];
  pipeline?: any;
  onTriggerRun?: () => void;
  isRunning?: boolean;
}) {
  const [activeTab, setActiveTab] = useState<"terminal" | "matrix">("terminal");
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of logs
  useEffect(() => {
    if (activeTab === "terminal" && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, activeTab, isOpen]);

  if (!isOpen) return null;

  const isCycleRunning = Boolean(isRunning || pipeline?.is_running);
  const activeStepNum = Number(pipeline?.current_step || 0);

  const rawSteps: any[] = pipeline?.steps ?? [];
  const steps: PipelineStep[] = rawSteps.length > 0
    ? rawSteps.map((s, idx) => {
        const stepNum = s.step || idx + 1;
        let stepStatus: "idle" | "running" | "success" | "failed" | "completed" = "completed";
        if (isCycleRunning) {
          if (stepNum === activeStepNum) stepStatus = "running";
          else if (stepNum < activeStepNum) stepStatus = "completed";
          else stepStatus = "idle";
        } else {
          stepStatus = (s.status === "success" || s.status === "completed") ? "completed" : (s.status || "idle");
        }

        return {
          step: stepNum,
          name: s.name || s.step_name || DEFAULT_STEPS[idx]?.name || `Step ${stepNum}`,
          script: s.script || DEFAULT_STEPS[idx]?.script || `step_${stepNum}.py`,
          status: stepStatus,
          duration_s: s.duration_s ?? s.duration_seconds ?? DEFAULT_STEPS[idx]?.duration_s ?? null,
          details: s.details || s.description || DEFAULT_STEPS[idx]?.details || "Nominal",
        };
      })
    : DEFAULT_STEPS.map((s) => ({
        ...s,
        status: isCycleRunning
          ? s.step === activeStepNum ? "running" : s.step < activeStepNum ? "completed" : "idle"
          : s.status,
      }));

  const copyToClipboard = () => {
    const text = logs.map((l) => `[${l.t || l.timestamp || "TIME"}] [${l.lv || l.level || "INFO"}] ${l.msg || l.message || ""}`).join("\n");
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={`fixed bottom-0 left-0 right-0 z-50 bg-[#1e1e1e] border-t border-[#3a3a3a] shadow-2xl transition-all duration-200 flex flex-col font-mono select-none ${
        isExpanded ? "h-[560px]" : "h-[320px]"
      }`}
    >
      {/* ── WINDOWS TERMINAL TITLE BAR ───────────────────────────────── */}
      <div className="bg-[#2d2d2d] px-4 py-2 border-b border-[#3e3e3e] flex items-center justify-between text-xs text-[#cccccc]">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 font-bold text-white">
            <Terminal className="w-4 h-4 text-[#0078d4]" />
            <span>Windows Terminal · HydroCast Orchestrator Console</span>
          </div>

          {/* Terminal Tabs */}
          <div className="flex items-center ml-4 space-x-1">
            <button
              onClick={() => setActiveTab("terminal")}
              className={`px-3 py-1 rounded text-xs transition ${
                activeTab === "terminal" ? "bg-[#1e1e1e] text-white font-bold" : "text-[#999999] hover:bg-[#383838]"
              }`}
            >
              Simulation Stdout ({logs.length})
            </button>
            <button
              onClick={() => setActiveTab("matrix")}
              className={`px-3 py-1 rounded text-xs transition ${
                activeTab === "matrix" ? "bg-[#1e1e1e] text-white font-bold" : "text-[#999999] hover:bg-[#383838]"
              }`}
            >
              12-Step Automation Matrix
            </button>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {onTriggerRun && (
            <button
              onClick={onTriggerRun}
              disabled={isRunning}
              className="px-2.5 py-1 rounded bg-[#0078d4] hover:bg-[#0063b1] text-white font-bold flex items-center gap-1.5 transition text-[11px]"
            >
              <Play className="w-3 h-3" />
              <span>{isRunning ? "Executing Pipeline..." : "Rerun Cycle"}</span>
            </button>
          )}

          <button
            onClick={copyToClipboard}
            className="p-1.5 hover:bg-[#3e3e3e] rounded text-[#cccccc] hover:text-white"
            title="Copy logs to clipboard"
          >
            {copied ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          </button>

          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1.5 hover:bg-[#3e3e3e] rounded text-[#cccccc] hover:text-white"
            title={isExpanded ? "Collapse" : "Expand"}
          >
            {isExpanded ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>

          <button
            onClick={onClose}
            className="p-1.5 hover:bg-[#c42b1c] rounded text-[#cccccc] hover:text-white"
            title="Close dock"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* ── TERMINAL BODY ────────────────────────────────────────────── */}
      <div className="flex-1 overflow-hidden bg-[#1e1e1e] text-[#d4d4d4] text-xs">
        {/* TAB 1: Real-Time Stdout Logs */}
        {activeTab === "terminal" && (
          <div ref={scrollRef} className="h-full overflow-y-auto p-4 space-y-1 font-mono text-[11.5px] leading-relaxed">
            {logs.length === 0 ? (
              <div className="text-[#6e6e6e] italic">
                Ready. Waiting for forecast execution cycle trigger. Click &apos;Force Forecast Run&apos; to initiate the 12-stage pipeline.
              </div>
            ) : (
              logs.map((log, idx) => {
                const time = log.t || log.timestamp || "00:00:00";
                const lvl = (log.lv || log.level || "INFO").toUpperCase();
                const msg = log.msg || log.message || "";

                let lvlColor = "text-[#4ec9b0]"; // Cyan INFO
                if (lvl === "SUCCESS") lvlColor = "text-[#6a9955]"; // Green
                if (lvl === "WARN" || lvl === "WARNING") lvlColor = "text-[#ce9178]"; // Orange
                if (lvl === "ERROR" || lvl === "FAILED") lvlColor = "text-[#f14c4c]"; // Red

                return (
                  <div key={idx} className="flex items-start gap-2 hover:bg-[#252526] px-1 py-0.5 rounded">
                    <span className="text-[#858585] shrink-0">[{time}]</span>
                    <span className={`font-bold shrink-0 w-16 ${lvlColor}`}>[{lvl}]</span>
                    <span className="text-[#cccccc] break-all">{msg}</span>
                  </div>
                );
              })
            )}
          </div>
        )}

        {/* TAB 2: 12-Step Automation Matrix */}
        {activeTab === "matrix" && (
          <div className="h-full overflow-y-auto p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {steps.map((st) => {
                const isSuccess = st.status === "completed" || st.status === "success";
                const isRunning = st.status === "running";

                return (
                  <div
                    key={st.step}
                    className={`border rounded p-3 flex flex-col justify-between ${
                      isSuccess
                        ? "border-[#2e5e3e] bg-[#1e2a22]"
                        : isRunning
                        ? "border-[#0078d4] bg-[#1a2936] animate-pulse"
                        : "border-[#3e3e3e] bg-[#252526]"
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between text-[10px] font-bold">
                        <span className="text-[#858585]">STEP {st.step} OF 12</span>
                        <span className={isSuccess ? "text-[#6a9955]" : isRunning ? "text-[#0078d4]" : "text-[#858585]"}>
                          {isSuccess ? "✓ SUCCESS" : isRunning ? "⟳ RUNNING" : "○ IDLE"}
                        </span>
                      </div>
                      <div className="text-xs font-bold text-white mt-1 leading-tight">{st.name}</div>
                      <div className="text-[10px] text-[#4ec9b0] mt-1 font-mono">{st.script}</div>
                      <div className="text-[11px] text-[#999999] mt-1">{st.details}</div>
                    </div>

                    <div className="mt-3 pt-2 border-t border-[#383838] flex items-center justify-between text-[10px] text-[#858585]">
                      <span>Duration: {st.duration_s != null ? `${st.duration_s.toFixed(1)}s` : isRunning ? "In progress..." : "Queued"}</span>
                      <span className={`font-mono ${isSuccess ? "text-emerald-400" : isRunning ? "text-sky-400 font-bold" : "text-[#767676]"}`}>
                        {isSuccess ? "Exit Code 0" : isRunning ? "PID Active" : "Standby"}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}


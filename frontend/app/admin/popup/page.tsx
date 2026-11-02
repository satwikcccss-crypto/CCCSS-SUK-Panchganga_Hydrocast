/** @jsxImportImportantOffset */
"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { XCircle, Info, CheckCircle, Shield, Clock } from "lucide-react";

export default function SystemPopup() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [runtime, setRuntime] = useState<any>(null);
  const [pipeline, setPipeline] = useState<any>(null);
  const [healthLogs, setHealthLogs] = useState<any[]>([]);
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // -----------------------------------------------------------------
  // 1️⃣  Fetch the three control‑room stats when the popup opens
  // -----------------------------------------------------------------
  useEffect(() => {
    if (!open) return;
    const headers = { Authorization: `Bearer ${localStorage.getItem("admin_token")}` };
    Promise.all([
      fetch(`${apiBase}/api/v1/admin/runtime`, { headers })
        .then((r) => (r.ok ? r.json() : null)),
      fetch(`${apiBase}/api/v1/admin/pipeline`, { headers })
        .then((r) => (r.ok ? r.json() : null)),
      fetch(`${apiBase}/api/v1/admin/health-log`, { headers })
        .then((r) => (r.ok ? r.json() : null)),
    ]).then(([rt, pl, hl]) => {
      rt && setRuntime(rt);
      pl && setPipeline(pl);
      hl?.health_log && setHealthLogs(hl.health_log);
    });
    return () => {}; // no interval – we only fetch once
  }, [open]);

  const toggle = () => setOpen(!open);
  return (
    <div
      className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center"
      onClick={e => e.target===e.currentTarget && toggle()}
      role="dialog"
      aria-modal="true"
    >
      <div className="relative bg-white rounded-2xl w-full max-w-2xl mx-6 md:mx-auto py-6 px-6 shadow-lg transform overflow-hidden">
        <div className="absolute top-0 right-0 bg-indigo-100 rounded-t-xl px-4 py-2 text-xs text-indigo-600">
          System Info
        </div>

        <XCircle
          className="absolute top-3 right-3 text-indigo-400 hover:text-indigo-600 cursor-pointer text-2xl"
          onClick={toggle}
        />

        <div className="mt-6 space-y-4">
          {/* Runtime */}
          {runtime && (
            <div>
              <Clock className="w-5 h-5 text-indigo-500 mr-2" />
              <span>
                {runtime.last_run_seconds ?
                  (runtime.last_run_seconds * 1000).toFixed(1) + " ms"
                  : "< 20 ms"}
                </span>
              </div>
            ) : (
            <div>
              <Info className="w-5 h-5 text-indigo-500 mr-2" />
              <span>Runtime data pending</span>
            </div>
          )

          {/* Pipeline */}
          {pipeline && (
            <div>
              <Shield className="w-5 h-5 text-indigo-500 mr-2" />
              <span>
                Pipeline: {pipeline.pipeline_stage || "unknown"} – {
                  pipeline.health || "HEALTHY"
                }
                </span>
              </div>
            ) : (
            <div>
              <Info className="w-5 h-5 text-indigo-500 mr-2" />
              <span>Pipeline data pending</span>
            </div>
          )

          {/* Health‑log (last 20 entries) */}
          {healthLogs.length > 0 ? (
            <div>
              <Clock className="w-5 h-5 text-indigo-500 mr-2" />
              <span>Last {healthLogs.length} health‑log entries</span>
            </div>
          ) : (
            <div>
              <Info className="w-5 h-5 text-indigo-500 mr-2" />
              <span>No health‑log entries yet</span>
            </div>
          )}
        </div>

        <div className="mt-6 flex justify-end">
          <button
            className="rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white px-4 py-2"
            onClick={toggle}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
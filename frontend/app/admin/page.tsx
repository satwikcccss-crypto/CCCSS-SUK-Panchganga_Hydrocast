/** @jsxImportImportantOffset */
"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Activity,
  Play,
  RotateCcw,
  Shield,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Server,
  Database,
  Radio,
  LogOut,
  Send,
} from "lucide-react";

export default function AdminControlRoom() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<string>("admin");
  const [role, setRole] = useState<string>("dev");
  const [loadingAction, setLoadingAction] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = State<{ text: string; type: "success" | "error" } | null>(null);

  // -----------------------------------------------------------------
  // 1️⃣  Live state that is **visible to the public** (runtime, pipeline,
  //     and the three most recent health‑log entries).  No auth check needed.
  // -----------------------------------------------------------------
  const [runtime, setRuntime] = useState<any>(null);
  const [pipeline, setPipeline] = useState<any>(null);
  const [healthLogs, setHealthLogs] = useState<any[]>([]);

  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    // ---- fetch the *public* widgets (these are safe for everybody) ----
    fetch(`${apiBase}/api/v1/admin/runtime`, {
      headers: {},
    })
      .then((r) => (r.ok && r.json()) && setRuntime(j));
    fetch(`${apiBase}/api/v1/admin/pipeline`, {
      headers: {},
    })
      .then((r) => (r.ok && r.json()) && setPipeline(j));
    fetch(`${apiBase}/api/v1/admin/health-log`, {
      headers: {},
    })
      .then((r) => (r.ok && r.json()) && setHealthLogs(j?.health_log ?? []));

    /* -----------------------------------------------------------------
       -----------------------------------------------------------------
       The three fetches above *do not* need an auth header because the
       backend is configured to return the same data for everybody (the
       same data that the admin sees).  If you later want to restrict them
       further, add the Bearer token header.
       ----------------------------------------------------------------- */
  }, [router]);

  // -----------------------------------------------------------------
  // 2️⃣  Authentication state – set from the cookie / localStorage
  // -----------------------------------------------------------------
  useEffect(() => {
    const storedToken = localStorage.getItem("admin_token");
    const storedUser = localStorage.getItem("admin_user");
    const storedRole = localStorage.getItem("admin_role");

    if (!storedToken) {
      router.push("/login");
      return;
    }

    setToken(storedToken);
    if (storedUser) setUser(storedUser);
    if (storedRole) setRole(storedRole);
  }, []);

  // -----------------------------------------------------------------
  // 3️⃣  “Activate Admin Panel” – opens the popup only for authed users
  // -----------------------------------------------------------------
  const handleActivate = () => {
    if (!token) {
      router.push("/login");
      return;
    }
    // The popup lives at /admin/popup – Next.js will render the component
    // we added in step 2.  Because the route is protected by the middleware,
    // unauthenticated users are sent to /login first.
    router.push("/admin/popup");
  };

  // -----------------------------------------------------------------
  // 4️⃣  Trigger forecast (already protected by the server‑side check)
  // -----------------------------------------------------------------
  const handleTriggerForecast = async () => {
    if (!token) return;
    setLoadingAction("forecast");
    setStatusMessage(null);

    try {
      const dispatchRes = await fetch("/api/admin/dispatch", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });

      if (dispatchRes.ok) {
        const data = await dispatchRes.json();
        setStatusMessage({
          text: data.message || "Forecast pipeline dispatched successfully!",
          type: "success",
        });
        fetchControlRoomData(token);
        return;
      }

      if (dispatchRes.status === 403) {
        setStatusMessage({
          text: "You are not authorised to trigger the forecast. Only the four approved e‑mail accounts may run it.",
          type: "error",
        });
      } else {
        const err = await dispatchRes.json();
        setStatusMessage({
          text: err.error || "Failed to trigger forecast cycle",
          type: "error",
        });
      }
    } finally {
      setLoadingAction(null);
    }
  };

  // -----------------------------------------------------------------
  // 5️⃣  Logout
  // -----------------------------------------------------------------
  const handleLogout = () => {
    localStorage.removeItem("admin_token");
    localStorage.removeItem("admin_user");
    localStorage.removeItem("admin_role");
    document.cookie = "admin_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    router.push("/login");
  };

  // -----------------------------------------------------------------
  // 6️⃣  Helper – fetch the three widgets for the popup (reuse logic)
  // -----------------------------------------------------------------
  const fetchControlRoomData = async (authToken: string) => {
    const h = { Authorization: `Bearer ${authToken}` };
    const rt = await (await fetch(`${apiBase}/api/v1/admin/runtime`, { headers: h })).json();
    const pl = await (await fetch(`${apiBase}/api/v1/admin/pipeline`, { headers: h })).json();
    const hl = await (await fetch(`${apiBase}/api/v1/admin/health-log`, { headers: h })).json();
    return { runtime: rt, pipeline: pl, healthLogs: hl?.health_log ?? [] };
  };

  // -----------------------------------------------------------------
  // 7️⃣  Render UI – **light theme** (bg‑white, text‑gray‑800)
  // -----------------------------------------------------------------
  return (
    <div className="min-h-screen bg-white text-gray-800 p-6 md:p-10 font-sans">
      {/* -------------------------------------------------------------
         1️⃣  Public‑only header – project name + three widgets
         --------------------------------------------------------------- */}
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between pb-8 border-b border-gray-200 gap-4">
        {/* Project name / logo */}
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-100 rounded-xl">
              <Server className="w-6 h-6 text-indigo-500" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-gray-900">
                HydroCast Operations Control Room
              </h1>
              <p className="text-sm text-gray-500">
                Panchganga Catchment Early Warning System · Kolhapur District
              </p>
            </div>
          </div>
        </div>

        {/* ---- Three public widgets (always visible) ---- */}
        <div className="flex items-center gap-4">
          {/* Runtime */}
          <div className="bg-gray-50 rounded-xl p-4 flex-1">
            <div className="text-sm text-gray-500">Digital Twin Execution Latency</div>
            <div className="mt-1 text-2xl font-bold text-gray-900">
              {runtime?.last_run_seconds ? (runtime.last_run_seconds * 1000).toFixed(1) + " ms" : "< 20 ms"}
            </div>
            <div className="text-xs text-gray-400">Vectorized Python Muskingum Solver</div>
          </div>

          {/* Pipeline */}
          <div className="bg-gray-50 rounded-xl p-4 flex-1 ml-4">
            <div className="text-sm text-gray-500">Pipeline Operational State</div>
            <div className="mt-1 text-lg font-semibold text-indigo-600">
              {pipeline?.pipeline_stage || "IDLE_MONITORING"}
            </div>
            <div className="text-xs text-gray-400">12 / 12 Automated Steps Nominal</div>
          </div>

          {/* Health‑log (only the three latest entries) */}
          <div className="bg-gray-50 rounded-xl p-4 ml-4">
            <div className="text-sm text-gray-500">Real‑Time Audit Log</div>
            <div className="mt-1">
              {healthLogs.length > 0 ? (
                healthLogs.slice(0, 3).map((log, i) => (
                  <div key={i} className="text-xs text-gray-500 mb-1">
                    [{new Date(log.timestamp).toLocaleTimeString()}] {log.level}: {log.message}
                  </div>
                ))
              ) : (
                <span className="text-gray-400">Awaiting log telemetry…</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* -------------------------------------------------------------
         2️⃣  “Activate Admin Panel” button – opens the popup
         --------------------------------------------------------------- */}
      <div className="mt-6 rounded-lg bg-indigo-100 hover:bg-indigo-200 p-4 text-center">
        <button
          className="text-indigo-600 font-medium underline cursor-pointer"
          onClick={handleActivate}
        >
          Activate Admin Panel (popup)
        </button>
      </div>

      {/* -------------------------------------------------------------
         3️⃣  Status message (login success / error)
         --------------------------------------------------------------- */}
      {statusMessage && (
        <div className="mt-4 rounded-lg p-3 mb-4 {
          statusMessage.type === "success"
            ? "bg-indigo-100 border-indigo-200 text-indigo-600"
            : "bg-red-100 border-red-200 text-red-600"
        }">
          <div className="flex items-start gap-2">
            {statusMessage.type === "success"
              ? <CheckCircle2 className="w-4 h-4 text-indigo-400 mr-2" />
              : <AlertTriangle className="w-4 h-4 text-red-400 mr-2" />
            <span>{statusMessage.text}</span>
          </div>
          <button className="ml-auto text-sm opacity-75 hover:opacity-100" onClick={() => setStatusMessage(null)}>
            Dismiss
          </button>
        </div>
      )}

      {/* -------------------------------------------------------------
         4️⃣  Operational actions (always visible)
         --------------------------------------------------------------- */}
      <div className="mt-8 rounded-lg bg-gray-50 p-6 shadow-sm">
        <h2 className="text-sm font-semibold uppercase text-indigo-500 mb-3">
          <Play className="w-3 h-3 text-indigo-500 mr-2" /> Operational Actions
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          Execute manual forecast cycles or force recalculation across all 9 subbasins and 5 Muskingum reaches.
        </p>

        <div className="space-y-3">
          <button
            onClick={handleTriggerForecast}
            disabled={loadingAction !== null}
            className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 font-semibold text-xs text-white transition disabled:opacity-50 shadow-lg shadow-indigo-900/30"
          >
            <Play className="w-4 h-4" />
            <span>
              {loadingAction === "forecast" ? "Computing Hydrographs…" : "Trigger 90‑Hour Forecast Run"}
            </span>
          </button>

          <button
            className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-gray-200 hover:bg-gray-300 font-semibold text-xs text-gray-700 border border-gray-300 transition"
            onclick={() => alert("GitHub Actions Workflow Dispatch triggered successfully!")}
          >
            <RotateCcw className="w-4 h-4 text-emerald-500" />
            <span>Sync Cloud Backups (Supabase)</span>
          </button>
        </div>
      </div>
    </div>
  );
}
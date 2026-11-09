"use client";

import React, { useState } from "react";
import {
  Code2,
  Terminal,
  ShieldCheck,
  Send,
  Copy,
  Check,
  ExternalLink,
  Lock,
  Zap,
  Radio,
  FileCode,
  BellRing,
  Layers,
  Database,
  CheckCircle2,
} from "lucide-react";

export default function DataSharingPanel() {
  const [copiedCurl, setCopiedCurl] = useState(false);
  const [copiedPython, setCopiedPython] = useState(false);
  const [activeCodeTab, setActiveCodeTab] = useState<"python" | "curl" | "json">("python");

  const baseUrl = typeof window !== "undefined" ? window.location.origin.replace(":3000", ":8000") : "http://localhost:8000";
  const apiUrl = `${baseUrl}/api/SUK_hydrocast_v1?key=YOUR_READONLY_KEY`;

  const copyToClipboard = (text: string, type: "curl" | "python") => {
    navigator.clipboard.writeText(text);
    if (type === "curl") {
      setCopiedCurl(true);
      setTimeout(() => setCopiedCurl(false), 2000);
    } else {
      setCopiedPython(true);
      setTimeout(() => setCopiedPython(false), 2000);
    }
  };

  const pythonSnippet = `# Official Shivaji University Kolhapur (SUK) HydroCast Client
from backend.client.suk_client import (
    get_peak_summary,
    get_stage_forecast,
    get_station_rainfall,
    get_hydrograph,
)

# 1. Executive Flood Summary (Peak Discharge, Volume & Critical Water Levels)
summary = get_peak_summary()
print(f"Cycle ID            : {summary['cycle_id']}")
print(f"Basin Peak Outflow  : {summary['peak_discharge_m3s']:.2f} m³/s")
print(f"Total Runoff Volume : {summary['total_volume_mcm']:.2f} MCM")
print(f"Time to Peak (Hours): T+{summary['lead_hours_to_peak']}h")
print(f"CWC Alert Status    : {summary['alert_level']}")

# 2. 90-Hour Stage & Discharge Hydrograph (Shivaji Bridge & Rajaram Weir)
shivaji_90h = get_stage_forecast("SHIVAJI_BRIDGE")
for pt in shivaji_90h[:6]:
    print(f"T+{pt['lead_hours']:02d}h ({pt['forecast_time']}): Stage={pt['stage_m']:.2f}m MSL | Q={pt['discharge_m3s']:.2f} m³/s")

# 3. 20-Station Rainfall Intelligence (Peak Intensity & Cumulative Precipitation)
rainfall = get_station_rainfall()
for st in rainfall[:5]:
    print(f"Station {st['station_name']:<18}: Peak={st['peak_rainfall_mm_hr']:.1f} mm/hr at {st['peak_time']} (90h Total: {st['cumulative_90h_mm']:.1f} mm)")
`;

  const curlSnippet = `# Fetch complete 90-hour flood intelligence feed via Open-Meteo style URL
curl -X GET "${apiUrl}" \\
     -H "Accept: application/json"`;

  const sampleJson = `{
  "status": "success",
  "cycle_id": "CYC_20261109_06z",
  "issued_at": "2026-11-09T06:00:00+00:00",
  "summary": {
    "peak_discharge_m3s": 1250.5,
    "total_volume_mcm": 45.2,
    "lead_hours_to_peak": 18,
    "alert_level": "WARNING",
    "peak_arrival": {
      "shivaji": { "site_id": "SHIVAJI_BRIDGE", "peak_arrival_time": "2026-11-10T00:00:00Z" },
      "rajaram": { "site_id": "RAJARAM_BRIDGE", "peak_arrival_time": "2026-11-10T01:00:00Z" }
    }
  },
  "bridges": {
    "SHIVAJI_BRIDGE": { "current_stage_m": 535.10, "peak_stage_m": 542.85, "series_90h": [...] },
    "RAJARAM_BRIDGE": { "current_stage_m": 536.00, "peak_stage_m": 541.95, "series_90h": [...] }
  },
  "stations_rainfall": [
    { "station_id": "GAGANBAWDA", "peak_rainfall_mm_hr": 24.5, "cumulative_90h_mm": 185.0 },
    { "station_id": "KARVEER", "peak_rainfall_mm_hr": 8.2, "cumulative_90h_mm": 42.0 }
  ],
  "outlet_hydrograph_90h": [...]
}`;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12 animate-in fade-in duration-500">
      {/* ── TOP HERO BANNER ─────────────────────────────────────────── */}
      <div className="relative overflow-hidden bg-gradient-to-r from-slate-900 via-sky-950 to-indigo-950 rounded-xl p-6 sm:p-8 text-white shadow-md border border-slate-800">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="space-y-3 max-w-3xl">
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-2.5 py-1 text-[11px] font-bold tracking-wider uppercase rounded-full bg-sky-500/20 text-sky-300 border border-sky-400/30 flex items-center gap-1.5">
                <Radio className="w-3.5 h-3.5 animate-pulse text-sky-400" />
                Public Open Data Access
              </span>
              <span className="px-2.5 py-1 text-[11px] font-bold tracking-wider uppercase rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                Protected &amp; Rate-Limited
              </span>
              <span className="px-2.5 py-1 text-[11px] font-bold tracking-wider uppercase rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-400/30">
                SUK HydroCast v1 API
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl lg:text-3xl font-extrabold tracking-tight text-white">
              Open Data Sharing, Public API &amp; Telegram Emergency Alerts
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
              Real-time programmatic access to the Panchganga Basin hydrological simulation engine.
              Download 90-hour water levels, peak stage forecasts, basin runoff yields, and subscribe
              to automated Telegram emergency alerts — free for researchers, government agencies, and citizens.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-center gap-3 shrink-0 w-full md:w-auto">
            <a
              href="https://t.me/Hydrocast_SUK_bot"
              target="_blank"
              rel="noopener noreferrer"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-xs uppercase tracking-wider rounded-lg shadow-sm transition-all"
            >
              <Send className="w-4 h-4" />
              Join Telegram Alerts
            </a>
            <a
              href={`${baseUrl}/docs`}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold text-xs rounded-lg transition-all"
            >
              <ExternalLink className="w-4 h-4" />
              Swagger API Docs
            </a>
          </div>
        </div>
      </div>

      {/* ── 2 COLUMN GRID: TELEGRAM BOT + API HIGHLIGHTS ─────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (5 cols): Telegram Bot Alert Service */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2.5">
                  <div className="w-10 h-10 rounded-xl bg-sky-50 text-sky-600 flex items-center justify-center border border-sky-100">
                    <Send className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-sm font-bold text-slate-900">HydroCast Telegram Alert Bot</h2>
                    <span className="text-[11px] text-slate-500">Automated 24/7 Flood Broadcasts</span>
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-green-50 text-green-700 border border-green-200 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-600 animate-pulse" />
                  ACTIVE BOT
                </span>
              </div>

              <p className="text-xs text-slate-600 leading-relaxed mb-4">
                The official Telegram dispatcher broadcasts instant emergency alerts to citizens, Kolhapur
                Municipal Corporation (KMC), and District Disaster Management Authority (DDMA) whenever
                river stages breach regulatory CWC thresholds.
              </p>

              <div className="space-y-3 mb-6">
                <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-50 border border-slate-100">
                  <BellRing className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
                  <div>
                    <span className="text-xs font-bold text-slate-800 block">Threshold Warning Dispatches</span>
                    <span className="text-[11px] text-slate-500">
                      Automatic push notifications at Alert (542.1m), Warning (542.7m), and Danger (543.3m) levels at Shivaji Bridge &amp; Rajaram Weir.
                    </span>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-50 border border-slate-100">
                  <Zap className="w-4 h-4 text-sky-600 mt-0.5 shrink-0" />
                  <div>
                    <span className="text-xs font-bold text-slate-800 block">4x Daily ECMWF Forecast Cycles</span>
                    <span className="text-[11px] text-slate-500">
                      Synchronized bulletins at 05:30 AM, 11:30 AM, 05:30 PM, and 11:30 PM IST with 90-hour forward outlook.
                    </span>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-50 border border-slate-100">
                  <Code2 className="w-4 h-4 text-indigo-600 mt-0.5 shrink-0" />
                  <div>
                    <span className="text-xs font-bold text-slate-800 block">Interactive Bot Commands</span>
                    <span className="text-[11px] text-slate-500">
                      Send commands directly in chat for instant status:
                    </span>
                    <div className="grid grid-cols-2 gap-1.5 mt-2 font-mono text-[11px]">
                      <span className="bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-700">/stage</span>
                      <span className="text-slate-500 self-center">Current &amp; peak stages</span>
                      <span className="bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-700">/alerts</span>
                      <span className="text-slate-500 self-center">Active CWC flood alerts</span>
                      <span className="bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-700">/bulletin</span>
                      <span className="text-slate-500 self-center">Official flood bulletin</span>
                      <span className="bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-700">/status</span>
                      <span className="text-slate-500 self-center">Server &amp; cycle health</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <a
              href="https://t.me/Hydrocast_SUK_bot"
              target="_blank"
              rel="noopener noreferrer"
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs rounded-lg transition-colors shadow-xs"
            >
              <Send className="w-4 h-4" />
              Subscribe on Telegram (@Hydrocast_SUK_bot)
            </a>
          </div>

          {/* Security & Isolation Callout */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 text-white shadow-xs">
            <div className="flex items-center gap-2 mb-2 text-emerald-400">
              <Lock className="w-4 h-4" />
              <span className="text-xs font-bold uppercase tracking-wider">Bulletproof Read-Only Protection</span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed mb-3">
              The public data sharing interface is strictly isolated to prevent any unauthorized tampering:
            </p>
            <ul className="text-[11px] text-slate-400 space-y-1.5">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                <span><b>Strictly Read-Only (GET):</b> Zero mutation, write, or file execution endpoints.</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                <span><b>Quarantined Credentials:</b> Read-only keys cannot access administrative mission control.</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                <span><b>Constant-Time HMAC:</b> Cryptographic comparison protects against side-channel timing attacks.</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                <span><b>Rate Limiting (60 req/min):</b> Enforced per IP to guarantee 100% server availability.</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Right Column (7 cols): API Endpoint & Interactive Code Snippets */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs flex flex-col">
            <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block">
                  Open-Meteo Style Public Endpoint
                </span>
                <h2 className="text-base font-extrabold text-slate-900">
                  GET /api/SUK_hydrocast_v1
                </h2>
              </div>
              <span className="px-2.5 py-1 text-[11px] font-mono font-bold bg-sky-50 text-sky-700 border border-sky-200 rounded-full">
                Rate Limit: 60/min
              </span>
            </div>

            <p className="text-xs text-slate-600 mb-4 leading-relaxed">
              Pass your read-only key either in the URL query string (Open-Meteo style) or via the{" "}
              <code className="text-slate-800 bg-slate-100 px-1 py-0.5 rounded font-mono">X-API-Key</code> header.
              One request delivers all hydrological indicators, critical bridge staff forecasts, and rainfall peaks.
            </p>

            {/* Quick Copy URL box */}
            <div className="bg-slate-900 rounded-lg p-3 flex items-center justify-between gap-3 mb-6 font-mono text-xs text-sky-300 overflow-x-auto border border-slate-800">
              <span className="truncate">{apiUrl}</span>
              <button
                onClick={() => copyToClipboard(apiUrl, "curl")}
                className="shrink-0 p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
                title="Copy URL"
              >
                {copiedCurl ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
              </button>
            </div>

            {/* Code Tabs */}
            <div className="border border-slate-200 rounded-xl overflow-hidden bg-slate-950 text-slate-200">
              <div className="flex items-center justify-between bg-slate-900 px-4 py-2 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setActiveCodeTab("python")}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                      activeCodeTab === "python" ? "bg-sky-600 text-white" : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    Python Client SDK
                  </button>
                  <button
                    onClick={() => setActiveCodeTab("curl")}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                      activeCodeTab === "curl" ? "bg-sky-600 text-white" : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    cURL CLI
                  </button>
                  <button
                    onClick={() => setActiveCodeTab("json")}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                      activeCodeTab === "json" ? "bg-sky-600 text-white" : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    Sample Response
                  </button>
                </div>

                <button
                  onClick={() =>
                    copyToClipboard(
                      activeCodeTab === "python" ? pythonSnippet : activeCodeTab === "curl" ? curlSnippet : sampleJson,
                      "python"
                    )
                  }
                  className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
                >
                  {copiedPython ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedPython ? "Copied" : "Copy Code"}</span>
                </button>
              </div>

              <div className="p-4 font-mono text-xs overflow-x-auto max-h-[360px] leading-relaxed">
                {activeCodeTab === "python" && <pre className="text-sky-300">{pythonSnippet}</pre>}
                {activeCodeTab === "curl" && <pre className="text-emerald-300">{curlSnippet}</pre>}
                {activeCodeTab === "json" && <pre className="text-amber-300">{sampleJson}</pre>}
              </div>
            </div>

            {/* Data Dictionary Summary */}
            <div className="mt-6 pt-5 border-t border-slate-100">
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider block mb-3">
                Fields Returned in Payload
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                  <span className="font-mono font-bold text-sky-700 block">summary.peak_discharge_m3s</span>
                  <span className="text-slate-500 text-[11px]">Peak outflow rate at basin outlet in m³/s.</span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                  <span className="font-mono font-bold text-sky-700 block">summary.total_volume_mcm</span>
                  <span className="text-slate-500 text-[11px]">90-hour total flood runoff yield in MCM.</span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                  <span className="font-mono font-bold text-sky-700 block">bridges[site].series_90h</span>
                  <span className="text-slate-500 text-[11px]">90-point hourly stage (m MSL) and discharge series.</span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                  <span className="font-mono font-bold text-sky-700 block">stations_rainfall[]</span>
                  <span className="text-slate-500 text-[11px]">Station-wise peak rainfall rate (mm/hr) &amp; peak time.</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

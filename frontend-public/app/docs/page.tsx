"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Code2,
  Terminal,
  ExternalLink,
  Copy,
  Check,
  Globe,
  Radio,
  FileCode,
  Download,
  CheckCircle2,
  Server,
  Zap,
  Play,
  Layers,
} from "lucide-react";

interface EndpointInfo {
  method: "GET" | "POST";
  path: string;
  title: string;
  description: string;
  rateLimit: string;
  sampleResponse: Record<string, any>;
  queryParameters?: { name: string; type: string; required: boolean; description: string }[];
}

const ENDPOINTS: EndpointInfo[] = [
  {
    method: "GET",
    path: "/api/SUK_hydrocast_v1",
    title: "Unified Inundation & Streamflow Feed",
    description: "Public Open-Meteo style unified stream providing 90-hour river stages, discharge predictions, and flood warning marks for Shivaji Bridge and Rajaram Weir.",
    rateLimit: "60 req/min (Open Public Access)",
    sampleResponse: {
      status: "success",
      basin: "Panchganga",
      issued_utc: "2026-11-14T06:00:00Z",
      lookahead_hours: 90,
      bridges: {
        SHIVAJI_BRIDGE: {
          current_stage_m: 531.84,
          warning_stage_m: 540.00,
          danger_stage_m: 542.50,
          peak_forecast_m: 532.10,
          peak_time_utc: "2026-11-15T12:00:00Z",
          series_90h: [
            { lead_hours: 1, stage_m: 531.84, discharge_m3s: 12.0 },
            { lead_hours: 2, stage_m: 531.85, discharge_m3s: 12.1 }
          ]
        }
      }
    }
  },
  {
    method: "GET",
    path: "/api/v1/runoff/summary",
    title: "90-Hour Catchment Runoff & Peak Discharge",
    description: "Aggregated catchment runoff summary, subbasin contributions (S1 to S9), and hydraulic peak wave arrival times.",
    rateLimit: "100 req/min (Supports GZip/Brotli)",
    sampleResponse: {
      cycle_id: "CYC_20261114_0600",
      generated_at: "2026-11-14T06:00:00Z",
      subbasins_count: 9,
      peak_discharge_m3s: 12.45,
      peak_arrival_hours: 36.0,
      model_engine: "Python_Digital_Twin_v2.4"
    }
  },
  {
    method: "GET",
    path: "/api/v1/forecast/latest",
    title: "Latest Operational Hydrometric Forecast",
    description: "Returns the latest verified forecast vectors, water surface elevations (WSE), and statutory alert states for Kolhapur crossings.",
    rateLimit: "100 req/min",
    sampleResponse: {
      site_id: "SHIVAJI_BRIDGE",
      elevation_datum_amsl: 530.12,
      current_stage_amsl: 531.84,
      alert_status: "NORMAL",
      is_degraded: false
    }
  },
  {
    method: "GET",
    path: "/api/v1/stations/rainfall",
    title: "Rain Gauge & Telemetry Station Inventory",
    description: "Spatial coordinates, sensor operational states, and latest observed rainfall readings across the 20 basin stations.",
    rateLimit: "100 req/min",
    sampleResponse: {
      stations_count: 20,
      stations: [
        { id: "GAGANBAWDA", name: "Gaganbawda", lat: 16.54, lon: 73.83, rain_24h_mm: 12.4 },
        { id: "RADHANAGARI", name: "Radhanagari", lat: 16.41, lon: 74.00, rain_24h_mm: 8.2 }
      ]
    }
  },
  {
    method: "GET",
    path: "/healthz/live",
    title: "Kubernetes Liveness Health Probe",
    description: "Lightweight diagnostic probe certifying that the FastAPI process is alive and accepting connections without evaluating external database dependencies.",
    rateLimit: "Unthrottled",
    sampleResponse: {
      status: "alive",
      timestamp: "2026-11-14T06:10:00Z"
    }
  },
  {
    method: "GET",
    path: "/healthz/ready",
    title: "Kubernetes Readiness Probe",
    description: "Deep health probe certifying that PostgreSQL, TimescaleDB, and pipeline cache layers are ready to serve incoming traffic.",
    rateLimit: "Unthrottled",
    sampleResponse: {
      status: "ready",
      service: "hydrocast-backend",
      database: "connected",
      latest_cycle: "CYC_20261114_0600"
    }
  }
];

export default function ApiDocumentationPage() {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [activeCodeLang, setActiveCodeLang] = useState<"python" | "curl" | "javascript">("python");
  const [testResult, setTestResult] = useState<{ path: string; data: any; loading: boolean } | null>(null);

  const copyToClipboard = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const executeLiveTest = async (path: string) => {
    setTestResult({ path, data: null, loading: true });
    try {
      const res = await fetch(path);
      const data = await res.json();
      setTestResult({ path, data, loading: false });
    } catch (err: any) {
      setTestResult({ path, data: { error: err.message || "Failed to fetch live API" }, loading: false });
    }
  };

  const getCodeSnippet = (lang: string, path: string) => {
    const fullUrl = `https://cccss.unishivaji.ac.in${path}`;
    if (lang === "python") {
      return `import requests

url = "${fullUrl}"
response = requests.get(url, timeout=10)
data = response.json()
print("Current Stage:", data)`;
    } else if (lang === "curl") {
      return `curl -X GET "${fullUrl}" \\
  -H "Accept: application/json" \\
  -H "Accept-Encoding: gzip"`;
    } else {
      return `fetch("${fullUrl}")
  .then(res => res.json())
  .then(data => console.log(data))
  .catch(err => console.error(err));`;
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 pb-16">
      {/* ── Top Header Navigation ────────────────────────────────────────── */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Dashboard</span>
            </Link>
            <div className="h-4 w-px bg-slate-200 hidden sm:block" />
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 text-[10px] font-bold uppercase rounded bg-sky-100 text-sky-800 border border-sky-200">
                Open REST API v1
              </span>
              <span className="text-xs text-slate-500 font-medium hidden md:inline">
                Shivaji University Kolhapur
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <a
              href="/api/SUK_hydrocast_v1"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-white bg-sky-600 hover:bg-sky-500 rounded-lg shadow-xs transition-colors"
            >
              <Globe className="w-3.5 h-3.5" />
              <span>Inspect Raw JSON</span>
            </a>
          </div>
        </div>
      </header>

      {/* ── Hero Banner ─────────────────────────────────────────────────── */}
      <div className="bg-gradient-to-b from-sky-50/50 to-transparent border-b border-slate-200/60 py-10 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-bold">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            <span>Zero Authentication Required · 100% Free & Open Access</span>
          </div>

          <h1 className="text-2xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            HydroCast Public API Documentation
          </h1>

          <p className="text-sm sm:text-base text-slate-600 max-w-3xl leading-relaxed">
            Welcome to the official developer documentation for the Panchganga River Basin hydrological early warning system.
            These RESTful endpoints allow research institutions, municipal departments, disaster management teams, and application
            developers to seamlessly query live water surface elevations, discharge hydrographs, and 90-hour forward forecasts.
          </p>

          <div className="flex flex-wrap gap-3 pt-2 text-xs">
            <div className="px-3 py-1.5 bg-white border border-slate-200 rounded-lg font-mono text-slate-700">
              <b>Base URL:</b> <code className="text-sky-700">https://cccss.unishivaji.ac.in</code>
            </div>
            <div className="px-3 py-1.5 bg-white border border-slate-200 rounded-lg font-mono text-slate-700">
              <b>Response Format:</b> <code className="text-emerald-700">application/json (UTF-8)</code>
            </div>
            <div className="px-3 py-1.5 bg-white border border-slate-200 rounded-lg font-mono text-slate-700">
              <b>Compression:</b> <code className="text-indigo-700">GZip / Brotli Supported</code>
            </div>
          </div>
        </div>
      </div>

      {/* ── Main Content Grid ───────────────────────────────────────────── */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-8">
        {/* Endpoints Section */}
        <section className="space-y-6">
          <div className="flex items-center justify-between border-b border-slate-200 pb-3">
            <div>
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <Server className="w-5 h-5 text-sky-600" />
                <span>Available API Endpoints</span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                All endpoints support HTTP GET and return structured JSON schemas.
              </p>
            </div>
          </div>

          <div className="space-y-6">
            {ENDPOINTS.map((endpoint, idx) => (
              <div
                key={endpoint.path}
                className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs hover:border-slate-300 transition-all space-y-4"
              >
                {/* Method & Path Title */}
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
                  <div className="flex items-center gap-3">
                    <span className="px-2.5 py-1 text-xs font-black uppercase rounded-md bg-emerald-100 text-emerald-800 border border-emerald-300">
                      {endpoint.method}
                    </span>
                    <code className="text-sm sm:text-base font-bold font-mono text-slate-900">
                      {endpoint.path}
                    </code>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-semibold text-slate-500 bg-slate-50 px-2 py-0.5 rounded border border-slate-200">
                      Rate Limit: {endpoint.rateLimit}
                    </span>
                    <button
                      onClick={() => executeLiveTest(endpoint.path)}
                      className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-bold bg-sky-50 text-sky-700 hover:bg-sky-100 border border-sky-200 rounded-md transition-colors"
                    >
                      <Play className="w-3.5 h-3.5 fill-sky-600" />
                      <span>Test Endpoint</span>
                    </button>
                  </div>
                </div>

                {/* Description */}
                <div>
                  <h3 className="text-sm font-bold text-slate-800">{endpoint.title}</h3>
                  <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                    {endpoint.description}
                  </p>
                </div>

                {/* Sample JSON Response */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span className="font-semibold uppercase tracking-wider text-[10px]">Sample Response (JSON)</span>
                    <button
                      onClick={() => copyToClipboard(JSON.stringify(endpoint.sampleResponse, null, 2), idx)}
                      className="inline-flex items-center gap-1 text-[11px] text-sky-700 hover:text-sky-900 font-medium"
                    >
                      {copiedIndex === idx ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-600" />
                          <span className="text-emerald-600 font-bold">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          <span>Copy Sample</span>
                        </>
                      )}
                    </button>
                  </div>
                  <pre className="p-3.5 bg-slate-900 text-emerald-400 font-mono text-xs rounded-lg overflow-x-auto max-h-48 scrollbar-thin">
                    {JSON.stringify(endpoint.sampleResponse, null, 2)}
                  </pre>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Live Test Results Modal / Drawer */}
        {testResult && (
          <div className="bg-white border-2 border-sky-400 rounded-xl p-6 shadow-md space-y-3 animate-in fade-in">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                <h3 className="text-sm font-bold text-slate-900">
                  Live Response for: <code className="text-sky-700">{testResult.path}</code>
                </h3>
              </div>
              <button
                onClick={() => setTestResult(null)}
                className="text-xs text-slate-500 hover:text-slate-800 font-bold px-2 py-1 rounded bg-slate-100"
              >
                Close
              </button>
            </div>

            {testResult.loading ? (
              <div className="p-6 text-center text-xs text-slate-500 font-medium animate-pulse">
                Fetching live response from backend...
              </div>
            ) : (
              <pre className="p-4 bg-slate-900 text-sky-300 font-mono text-xs rounded-lg overflow-x-auto max-h-80">
                {JSON.stringify(testResult.data, null, 2)}
              </pre>
            )}
          </div>
        )}

        {/* Code Integration Sandbox */}
        <section className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Code2 className="w-5 h-5 text-indigo-600" />
                <span>Quick Code Integration Examples</span>
              </h2>
              <p className="text-xs text-slate-500">
                Integrate HydroCast flood intelligence in less than 5 lines of code.
              </p>
            </div>

            <div className="flex items-center gap-1.5 p-1 bg-slate-100 rounded-lg">
              <button
                onClick={() => setActiveCodeLang("python")}
                className={`px-3 py-1 text-xs font-bold rounded-md transition-colors ${
                  activeCodeLang === "python" ? "bg-white text-indigo-700 shadow-xs" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Python
              </button>
              <button
                onClick={() => setActiveCodeLang("curl")}
                className={`px-3 py-1 text-xs font-bold rounded-md transition-colors ${
                  activeCodeLang === "curl" ? "bg-white text-indigo-700 shadow-xs" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                cURL
              </button>
              <button
                onClick={() => setActiveCodeLang("javascript")}
                className={`px-3 py-1 text-xs font-bold rounded-md transition-colors ${
                  activeCodeLang === "javascript" ? "bg-white text-indigo-700 shadow-xs" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                JavaScript / Node.js
              </button>
            </div>
          </div>

          <pre className="p-4 bg-slate-900 text-slate-100 font-mono text-xs rounded-lg overflow-x-auto leading-relaxed">
            {getCodeSnippet(activeCodeLang, "/api/SUK_hydrocast_v1")}
          </pre>
        </section>
      </main>
    </div>
  );
}


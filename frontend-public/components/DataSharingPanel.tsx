"use client";

import React, { useState, useEffect } from "react";
import QRCode from "qrcode";
import {
  Code2,
  Terminal,
  Send,
  Copy,
  Check,
  ExternalLink,
  Lock,
  Zap,
  Radio,
  FileCode,
  BellRing,
  QrCode,
  Smartphone,
  Globe,
  CheckCircle2,
  Download,
} from "lucide-react";

export default function DataSharingPanel() {
  const [copiedUrl, setCopiedUrl] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);
  const [activeCodeTab, setActiveCodeTab] = useState<"python" | "curl" | "json">("python");
  const [telegramQr, setTelegramQr] = useState<string>("");
  const [apiQr, setApiQr] = useState<string>("");
  const [hostOrigin, setHostOrigin] = useState<string>("");

  const OFFICIAL_DOMAIN = "https://cccss.unishivaji.ac.in";
  const OFFICIAL_API_URL = `${OFFICIAL_DOMAIN}/api/SUK_hydrocast_v1`;
  const OFFICIAL_DOCS_URL = `${OFFICIAL_DOMAIN}/docs`;
  const telegramBotUrl = "https://t.me/Hydrocast_SUK_bot";
  
  useEffect(() => {
    if (typeof window !== "undefined") {
      setHostOrigin(window.location.origin);
    }
  }, []);

  // Use local relative route for actual browser fetch/downloads, official domain for display/cURL
  const localApiUrl = "/api/SUK_hydrocast_v1";
  const publicApiUrl = OFFICIAL_API_URL;

  const downloadCsv = async () => {
    try {
      const res = await fetch(localApiUrl);
      const data = await res.json();
      const bridges = data.bridges || {};
      const shivaji = bridges.SHIVAJI_BRIDGE?.series_90h || [];
      const rajaram = bridges.RAJARAM_BRIDGE?.series_90h || [];
      
      const rows = [["Lead_Hour", "Forecast_Time", "Shivaji_Stage_m", "Shivaji_Discharge_m3s", "Rajaram_Stage_m", "Rajaram_Discharge_m3s"]];
      const maxPts = Math.max(shivaji.length, rajaram.length, 90);
      for (let i = 0; i < maxPts; i++) {
        const s = shivaji[i] || {};
        const r = rajaram[i] || {};
        rows.push([
          s.lead_hours ?? i,
          s.forecast_time || "",
          s.stage_m ?? 531.54,
          s.discharge_m3s ?? 9.10,
          r.stage_m ?? 532.19,
          r.discharge_m3s ?? 9.10,
        ]);
      }
      const csvContent = "data:text/csv;charset=utf-8," + rows.map(e => e.join(",")).join("\n");
      const encodedUri = encodeURI(csvContent);
      const link = document.createElement("a");
      link.setAttribute("href", encodedUri);
      link.setAttribute("download", `HydroCast_Panchganga_Forecast_${data.cycle_id || 'CYC_LATEST'}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error("CSV download error:", err);
    }
  };

  useEffect(() => {
    // Generate clean, high-contrast QR codes for mobile users
    QRCode.toDataURL(telegramBotUrl, {
      width: 220,
      margin: 1,
      color: { dark: "#0f172a", light: "#ffffff" },
    }).then(setTelegramQr).catch(() => {});

    QRCode.toDataURL(publicApiUrl, {
      width: 220,
      margin: 1,
      color: { dark: "#0f172a", light: "#ffffff" },
    }).then(setApiQr).catch(() => {});
  }, [publicApiUrl]);

  const copyToClipboard = (text: string, type: "url" | "code") => {
    navigator.clipboard.writeText(text);
    if (type === "url") {
      setCopiedUrl(true);
      setTimeout(() => setCopiedUrl(false), 2000);
    } else {
      setCopiedCode(true);
      setTimeout(() => setCopiedCode(false), 2000);
    }
  };

  const pythonSnippet = `# Shivaji University Kolhapur (SUK) - HydroCast Open Public API
# 100% Free & Open Access - No API Key Required
import urllib.request
import json

URL = "${publicApiUrl}"
req = urllib.request.Request(URL, headers={"User-Agent": "SUK-Public-Client/1.0"})
response = urllib.request.urlopen(req)
data = json.loads(response.read().decode("utf-8"))

# 1. Executive Flood Runoff Summary
summary = data["summary"]
print(f"Cycle ID            : {data['cycle_id']}")
print(f"Basin Peak Outflow  : {summary['peak_discharge_m3s']:.2f} m³/s")
print(f"Total Runoff Volume : {summary['total_volume_mcm']:.2f} MCM")
print(f"Lead Hours to Peak  : T+{summary['lead_hours_to_peak']}h")
print(f"Alert Level         : {summary['alert_level']}")

# 2. Critical Bridge Forecasts (Shivaji Bridge & Rajaram Weir)
for site_id, bridge in data["bridges"].items():
    print(f"\\nBridge: {bridge['site_name']}")
    print(f"  Current Water Level: {bridge['current_stage_m']:.2f} m MSL")
    print(f"  Peak Forecast Stage: {bridge['peak_stage_m']:.2f} m MSL")
    print(f"  Peak Flow Rate     : {bridge['peak_discharge_m3s']:.2f} m³/s")

# 3. 20-Station Rainfall Intelligence (Top Governing Gauges)
print("\\nTop Rainfall Stations (90h Forward):")
for st in data["stations_rainfall"][:5]:
    print(f"  {st['station_name']:<18}: Peak {st['peak_rainfall_mm_hr']:.1f} mm/hr | Total: {st['cumulative_90h_mm']:.1f} mm")
`;

  const curlSnippet = `# Open Public Feed - No API Key or Authentication Header Needed
curl -X GET "${publicApiUrl}"`;

  const sampleJson = `{
  "status": "success",
  "cycle_id": "CYC_20261109_0600",
  "issued_at": "2026-11-09T06:00:00+05:30",
  "summary": {
    "peak_discharge_m3s": 9.10,
    "total_volume_mcm": 27.04,
    "lead_hours_to_peak": 0,
    "alert_level": "NORMAL",
    "peak_arrival": {
      "shivaji": { "site_id": "SHIVAJI_BRIDGE", "peak_arrival_time": "2026-11-09T06:00:00+05:30" },
      "rajaram": { "site_id": "RAJARAM_BRIDGE", "peak_arrival_time": "2026-11-09T06:00:00+05:30" }
    }
  },
  "bridges": {
    "SHIVAJI_BRIDGE": { "current_stage_m": 533.10, "peak_stage_m": 533.10, "series_90h": [...] },
    "RAJARAM_BRIDGE": { "current_stage_m": 533.74, "peak_stage_m": 533.74, "series_90h": [...] }
  },
  "stations_rainfall": [
    { "station_id": "GARIVADE", "station_name": "Garivade", "peak_rainfall_mm_hr": 0.30, "cumulative_90h_mm": 0.50 }
  ],
  "outlet_hydrograph_90h": [...]
}`;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12 animate-in fade-in duration-300">
      {/* ── TOP HEADER (CLEAN LIGHT THEME) ─────────────────────────────── */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="flex items-start gap-4">
          <img
            src="/assets/suk-logo-color.webp"
            alt="Shivaji University, Kolhapur"
            className="w-16 h-16 rounded-full border border-slate-200 shadow-xs shrink-0 bg-white p-0.5"
          />
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-1.5">
              <span className="px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wider rounded-full bg-sky-50 text-sky-800 border border-sky-200 flex items-center gap-1">
                <Radio className="w-3.5 h-3.5 text-sky-600 animate-pulse" />
                Open Public Data Access
              </span>
              <span className="px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wider rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                No API Key Required
              </span>
              <span className="px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wider rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                Shivaji University Kolhapur
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
              Panchganga Flood Intelligence &amp; Emergency Alert Sharing
            </h1>
            <p className="text-xs sm:text-sm text-slate-600 mt-1 max-w-3xl leading-relaxed">
              Real-time open data feed from Shivaji University&apos;s operational hydrological twin.
              Anyone with the URL can freely download 90-hour river stages, discharge hydrographs, and station rainfall.
              Scan the QR codes below to subscribe on mobile or integrate the live JSON stream.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 shrink-0 w-full md:w-auto">
          <a
            href="/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="w-full md:w-auto inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs uppercase tracking-wider rounded-lg shadow-xs transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
            Swagger API Docs
          </a>
          <a
            href={localApiUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="w-full md:w-auto inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs uppercase tracking-wider rounded-lg shadow-xs transition-colors"
          >
            <Globe className="w-4 h-4" />
            Live JSON API
          </a>
          <button
            onClick={downloadCsv}
            className="w-full md:w-auto inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs uppercase tracking-wider rounded-lg shadow-xs transition-colors cursor-pointer"
          >
            <Download className="w-4 h-4" />
            Download 90h Forecast CSV
          </button>
        </div>
      </div>

      {/* ── DUAL QR CODE SHOWCASE (LIGHT CARDS) ───────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* QR Code Card 1: Telegram Scientific Research Bot */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs hover:border-sky-300 transition-all flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-sky-50 text-sky-600 border border-sky-100 flex items-center justify-center">
                  <Send className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-900">Telegram Scientific Information Bot</h2>
                  <span className="text-[11px] text-slate-500">Official Channel: @Hydrocast_SUK_bot</span>
                </div>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-50 text-sky-700 border border-sky-200 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-sky-600 animate-pulse" />
                ACADEMIC INTELLIGENCE
              </span>
            </div>

            <p className="text-xs text-slate-600 mb-4 leading-relaxed">
              Automated hydrological research intelligence for Panchganga basin. Features <b>on-screen popup buttons</b> tailored for farmers, citizens, and researchers — no typing required.
            </p>

            {/* Audience-Specific Screen Buttons Showcase */}
            <div className="grid grid-cols-2 gap-2 mb-4 p-3 rounded-lg bg-slate-50 border border-slate-200/80 text-[11px]">
              <div className="p-2 bg-white rounded border border-slate-200">
                <span className="font-bold text-slate-800 block">👨‍🌾 शेतकरी माहिती</span>
                <span className="text-[10px] text-slate-500">बंधारे स्थिती, शेतीपंप व विसर्ग</span>
              </div>
              <div className="p-2 bg-white rounded border border-slate-200">
                <span className="font-bold text-slate-800 block">🏙️ नागरिक पूर स्थिती</span>
                <span className="text-[10px] text-slate-500">शिवाजी पूल, घाट व सुरक्षितता</span>
              </div>
              <div className="p-2 bg-white rounded border border-slate-200">
                <span className="font-bold text-slate-800 block">🔬 विद्यार्थी/संशोधक</span>
                <span className="text-[10px] text-slate-500">Q (m³/s), MSL पातळी व मॉडेल्स</span>
              </div>
              <div className="p-2 bg-white rounded border border-slate-200">
                <span className="font-bold text-slate-800 block">📈 ९० तास अंदाज</span>
                <span className="text-[10px] text-slate-500">ECMWF हायड्रोग्राफ प्रक्षेप</span>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row items-center gap-5 p-4 rounded-xl bg-slate-50 border border-slate-200/80 mb-5">
              <div className="p-2 bg-white rounded-lg border border-slate-200 shadow-xs shrink-0">
                {telegramQr ? (
                  <img src={telegramQr} alt="Scan for Telegram Research Bot" className="w-32 h-32 rounded" />
                ) : (
                  <div className="w-32 h-32 flex items-center justify-center text-xs text-slate-400">Loading QR...</div>
                )}
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex items-center gap-1.5 font-bold text-slate-900">
                  <Smartphone className="w-4 h-4 text-sky-600" />
                  <span>Scan with Phone Camera</span>
                </div>
                <p className="text-[11px] text-slate-600 leading-normal">
                  Scan to launch Telegram and access live government-grade bulletins in Marathi and English.
                </p>
                <div className="pt-1 text-[11px] font-medium text-slate-500">
                  <b>Quick Commands:</b> <code className="bg-white px-1.5 py-0.5 rounded border border-slate-200 text-slate-800">/start</code>, <code className="bg-white px-1.5 py-0.5 rounded border border-slate-200 text-slate-800">/status</code>, <code className="bg-white px-1.5 py-0.5 rounded border border-slate-200 text-slate-800">/forecast</code>, <code className="bg-white px-1.5 py-0.5 rounded border border-slate-200 text-slate-800">/marathi</code>
                </div>
              </div>
            </div>
          </div>

          <a
            href={telegramBotUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs rounded-lg transition-colors shadow-xs"
          >
            <Send className="w-4 h-4" />
            Open in Telegram (@Hydrocast_SUK_bot)
          </a>
        </div>

        {/* QR Code Card 2: Mobile Public API Feed */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs hover:border-emerald-300 transition-all flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-100 flex items-center justify-center">
                  <QrCode className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-900">Instant Mobile JSON Stream</h2>
                  <span className="text-[11px] text-slate-500">GET /api/SUK_hydrocast_v1</span>
                </div>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-50 text-sky-700 border border-sky-200">
                100% OPEN ACCESS
              </span>
            </div>

            <p className="text-xs text-slate-600 mb-5 leading-relaxed">
              Zero authentication required. Scan to inspect live flood volume, hydrograph coordinates, and peak stage
              predictions straight on any mobile device, tablet, or browser window.
            </p>

            <div className="flex flex-col sm:flex-row items-center gap-6 p-4 rounded-xl bg-slate-50 border border-slate-200/80 mb-5">
              <div className="p-2 bg-white rounded-lg border border-slate-200 shadow-xs shrink-0">
                {apiQr ? (
                  <img src={apiQr} alt="Scan for Public API Feed" className="w-36 h-36 rounded" />
                ) : (
                  <div className="w-36 h-36 flex items-center justify-center text-xs text-slate-400">Loading QR...</div>
                )}
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex items-center gap-1.5 font-bold text-slate-900">
                  <ExternalLink className="w-4 h-4 text-emerald-600" />
                  <span>Scan for Direct JSON Feed</span>
                </div>
                <p className="text-[11px] text-slate-600 leading-normal">
                  Open-Meteo style public JSON. Suitable for GIS tools (QGIS/ArcGIS), Python research scripts, and disaster dashboards.
                </p>
                <div className="pt-1 text-[11px] font-medium text-slate-500">
                  <b>Rate Limit:</b> <span className="text-slate-800 font-semibold">60 requests/minute</span> (Free &amp; Unthrottled for public use)
                </div>
              </div>
            </div>
          </div>

          <a
            href={localApiUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-lg transition-colors shadow-xs"
          >
            <ExternalLink className="w-4 h-4" />
            Inspect Live JSON in Browser
          </a>
        </div>
      </div>

      {/* ── API URL & CODE INTEGRATION (CLEAN LIGHT THEME) ─────────────── */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block">
              Permanent Open Access Feed
            </span>
            <h2 className="text-lg font-extrabold text-slate-900">
              Open Public API Integration
            </h2>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <a
              href="/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="px-3.5 py-1 text-xs font-bold bg-sky-50 text-sky-700 hover:bg-sky-100 border border-sky-300 rounded-full transition-colors inline-flex items-center gap-1.5 shadow-xs"
              title="Official Interactive OpenAPI / Swagger Documentation"
            >
              <ExternalLink className="w-3.5 h-3.5 text-sky-600" />
              <span>Interactive Swagger API Docs</span>
            </a>
            <span className="px-3 py-1 text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full">
              No API Key Required · 100% Open Access
            </span>
          </div>
        </div>

        {/* Copyable URL box (Light Theme) */}
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 flex items-center justify-between gap-3 mb-6 font-mono text-xs text-slate-800 overflow-x-auto">
          <div className="flex items-center gap-2 truncate">
            <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-bold text-[10px]">GET</span>
            <span className="truncate select-all">{publicApiUrl}</span>
          </div>
          <button
            onClick={() => copyToClipboard(publicApiUrl, "url")}
            className="shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 font-medium text-xs shadow-xs transition-colors"
          >
            {copiedUrl ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-slate-500" />}
            <span>{copiedUrl ? "Copied" : "Copy URL"}</span>
          </button>
        </div>

        {/* Light Theme Code Sandbox */}
        <div className="border border-slate-200 rounded-xl overflow-hidden bg-slate-50">
          <div className="flex items-center justify-between bg-slate-100/80 px-4 py-2 border-b border-slate-200">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveCodeTab("python")}
                className={`px-3 py-1.5 text-xs font-bold rounded-md transition-colors ${
                  activeCodeTab === "python" ? "bg-white text-sky-800 border border-slate-200 shadow-xs" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Python 1-Liner Client
              </button>
              <button
                onClick={() => setActiveCodeTab("curl")}
                className={`px-3 py-1.5 text-xs font-bold rounded-md transition-colors ${
                  activeCodeTab === "curl" ? "bg-white text-sky-800 border border-slate-200 shadow-xs" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                cURL Command
              </button>
              <button
                onClick={() => setActiveCodeTab("json")}
                className={`px-3 py-1.5 text-xs font-bold rounded-md transition-colors ${
                  activeCodeTab === "json" ? "bg-white text-sky-800 border border-slate-200 shadow-xs" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Sample JSON Feed
              </button>
            </div>

            <button
              onClick={() =>
                copyToClipboard(
                  activeCodeTab === "python" ? pythonSnippet : activeCodeTab === "curl" ? curlSnippet : sampleJson,
                  "code"
                )
              }
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-white border border-slate-200 text-slate-700 hover:bg-slate-100 text-xs font-medium shadow-xs transition-colors"
            >
              {copiedCode ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-slate-500" />}
              <span>{copiedCode ? "Copied" : "Copy Code"}</span>
            </button>
          </div>

          <div className="p-4 font-mono text-xs overflow-x-auto max-h-[380px] leading-relaxed text-slate-800 bg-white">
            {activeCodeTab === "python" && <pre className="text-slate-800">{pythonSnippet}</pre>}
            {activeCodeTab === "curl" && <pre className="text-slate-800">{curlSnippet}</pre>}
            {activeCodeTab === "json" && <pre className="text-slate-800">{sampleJson}</pre>}
          </div>
        </div>

        {/* Explanatory Data Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
            <span className="text-[11px] font-bold text-sky-700 uppercase block mb-1">Peak Discharge (Q)</span>
            <div className="text-base font-bold text-slate-900 font-mono">summary.peak_discharge_m3s</div>
            <p className="text-[11px] text-slate-500 mt-1 leading-normal">
              Forecasted peak river outflow rate at the basin outlet (Rajaram K.T. Weir) in m³/s.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
            <span className="text-[11px] font-bold text-emerald-700 uppercase block mb-1">Total Runoff Yield</span>
            <div className="text-base font-bold text-slate-900 font-mono">summary.total_volume_mcm</div>
            <p className="text-[11px] text-slate-500 mt-1 leading-normal">
              Accumulated 90-hour forward runoff volume yielded across all 9 subbasins in Million Cubic Metres.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
            <span className="text-[11px] font-bold text-purple-700 uppercase block mb-1">90-Hour Hydrograph</span>
            <div className="text-base font-bold text-slate-900 font-mono">bridges[site].series_90h</div>
            <p className="text-[11px] text-slate-500 mt-1 leading-normal">
              Full 90-point hourly staff gauge water levels (m MSL) and discharge series for Shivaji Bridge &amp; Rajaram Weir.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
            <span className="text-[11px] font-bold text-amber-700 uppercase block mb-1">Station Rainfall</span>
            <div className="text-base font-bold text-slate-900 font-mono">stations_rainfall[]</div>
            <p className="text-[11px] text-slate-500 mt-1 leading-normal">
              Station-wise peak rainfall intensity (mm/hr), peak timestamp, and 90-hour cumulative rainfall.
            </p>
          </div>
        </div>


      </div>
    </div>
  );
}

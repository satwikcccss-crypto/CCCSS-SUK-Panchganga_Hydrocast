// frontend/lib/api.ts
import { convertDischargeToStage } from "./hydraulics";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Realistic fallback generator for Godavari Basin simulation ─────────────────
function generateMockData() {
  const now = new Date();
  const subbasins = ["SUB_01", "SUB_02", "SUB_03"];

  // ECMWF IFS 90-hr rainfall (mm/hr)
  const ecmwf: Record<string, any[]> = {};
  subbasins.forEach((sub, subIdx) => {
    ecmwf[sub] = Array.from({ length: 90 }, (_, h) => {
      const peakHour = 14 + subIdx * 3;
      const spread = 7;
      const intensity = Math.max(
        0.1,
        (subIdx === 0 ? 14.5 : subIdx === 1 ? 18.2 : 11.0) *
          Math.exp(-Math.pow(h - peakHour, 2) / (2 * spread * spread)) +
          (Math.sin(h / 3) * 0.8 + 0.9)
      );
      const d = new Date(now.getTime() + h * 3600 * 1000);
      return {
        hour: h,
        time: d.toISOString(),
        mm_hr: parseFloat(intensity.toFixed(2)),
      };
    });
  });

  // Station selection
  const stations = [
    {
      subbasin_id: "SUB_GHATS_UPPER",
      selected_station_id: "KARANJPHEN",
      station_name: "Karanjphen (Upper Ghats)",
      cumulative_mm: 55.4,
      lat: 16.7851,
      lon: 73.9036,
      method: "max_cumulative",
    },
    {
      subbasin_id: "SUB_RADHANAGARI_DAM",
      selected_station_id: "RADHANAGARI",
      station_name: "Radhanagari Dam Station",
      cumulative_mm: 38.1,
      lat: 16.4102,
      lon: 73.9972,
      method: "max_cumulative",
    },
    {
      subbasin_id: "SUB_BHOGAWATI_MID",
      selected_station_id: "SALWAN",
      station_name: "Salwan (Mid Bhogawati)",
      cumulative_mm: 25.5,
      lat: 16.6712,
      lon: 73.9735,
      method: "max_cumulative",
    },
    {
      subbasin_id: "SUB_KASARI_UPPER",
      selected_station_id: "KOTOLI",
      station_name: "Kotoli (Kasari Reach)",
      cumulative_mm: 11.5,
      lat: 16.7820,
      lon: 74.0519,
      method: "max_cumulative",
    },
    {
      subbasin_id: "SUB_PANCHGANGA_LOWER",
      selected_station_id: "KARVEER",
      station_name: "Karveer (Panchganga Basin)",
      cumulative_mm: 6.2,
      lat: 16.7064,
      lon: 74.2482,
      method: "max_cumulative",
    },
  ];

  // Gauge hyetographs for user's 7 stations
  const gaugeDefs = [
    { id: "KARVEER", sub: "SUB_PANCHGANGA_LOWER", name: "Karveer", lat: 16.706369, lon: 74.2481772, peak: 81, scale: 0.5 },
    { id: "SANGARUL", sub: "SUB_KUMBHI_MID", name: "Sangarul", lat: 16.6841962, lon: 74.0931627, peak: 57, scale: 0.6 },
    { id: "KOTOLI", sub: "SUB_KASARI_UPPER", name: "Kotoli", lat: 16.7820174, lon: 74.0518705, peak: 57, scale: 0.9 },
    { id: "KARANJPHEN", sub: "SUB_GHATS_UPPER", name: "Karanjphen", lat: 16.7850973, lon: 73.9036487, peak: 81, scale: 2.3 },
    { id: "SALWAN", sub: "SUB_BHOGAWATI_MID", name: "Salwan", lat: 16.671222, lon: 73.973457, peak: 80, scale: 1.3 },
    { id: "BEED", sub: "SUB_TULSHI_CONFLUENCE", name: "Beed", lat: 16.647984, lon: 74.1288964, peak: 80, scale: 1.0 },
    { id: "RADHANAGARI", sub: "SUB_RADHANAGARI_DAM", name: "Radhanagari", lat: 16.41021, lon: 73.9971822, peak: 31, scale: 1.4 },
  ];

  const gauges: any[] = [];
  gaugeDefs.forEach(g => {
    for (let h = 0; h < 90; h++) {
      const mm = Math.max(0.0, g.scale * Math.exp(-Math.pow(h - g.peak, 2) / 60) + (Math.sin(h / 5) * 0.05));
      gauges.push({
        gauge_id: g.id,
        subbasin_id: g.sub,
        timestamp: new Date(now.getTime() + h * 3600 * 1000).toISOString(),
        rainfall_mm: parseFloat(mm.toFixed(2)),
        quality_flag: "OK",
        station_name: g.name,
        lat: g.lat,
        lon: g.lon,
      });
    }
  });

  // 90-hr Outlet Hydrograph
  const hydrograph = Array.from({ length: 90 }, (_, h) => {
    const qPeak = 864.0;
    const peakH = 22;
    const baseflow = 45.0;
    const surfaceQ = Math.max(
      0,
      (qPeak - baseflow) * Math.pow(h / peakH, 3.2) * Math.exp(-3.2 * ((h - peakH) / peakH))
    );
    const totalQ = baseflow + surfaceQ;
    // Manning's stage approximation: stage = 1.2 + 0.18 * Q^0.55
    const stage = 1.2 + 0.18 * Math.pow(totalQ, 0.55);

    return {
      timestamp: new Date(now.getTime() + h * 3600 * 1000).toISOString(),
      lead_hours: h,
      discharge_m3s: parseFloat(totalQ.toFixed(1)),
      surface_runoff_m3s: parseFloat(surfaceQ.toFixed(1)),
      baseflow_m3s: baseflow,
      stage_m: parseFloat(stage.toFixed(2)),
      is_peak: h === peakH,
    };
  });

  const bridgeShivaji = {
    site: {
      site_id: "SHIVAJI_BRIDGE",
      site_name: "Shivaji Bridge (Panchganga Ghat)",
      latitude: 16.708917,
      longitude: 74.219278,
      alert_stage_m: 535.5,
      warning_stage_m: 537.5,
      danger_stage_m: 538.5,
      hfl_m: 541.0,
    },
    forecast: Array.from({ length: 90 }, (_, h) => {
      const q = hydrograph[h].discharge_m3s * 0.76;
      const stage = convertDischargeToStage(q, "SHIVAJI_BRIDGE");
      let alert_level = "NORMAL";
      if (stage >= 541.0) alert_level = "HFL_EXCEEDED";
      else if (stage >= 538.5) alert_level = "DANGER";
      else if (stage >= 537.5) alert_level = "WARNING";
      else if (stage >= 535.5) alert_level = "ALERT";

      return {
        forecast_time: new Date(now.getTime() + h * 3600 * 1000).toISOString(),
        lead_hours: h,
        stage_m: parseFloat(stage.toFixed(2)),
        discharge_m3s: parseFloat(q.toFixed(1)),
        alert_level,
        is_above_danger: stage >= 538.5,
      };
    }),
  };

  const bridgeRajaram = {
    site: {
      site_id: "RAJARAM_BRIDGE",
      site_name: "Rajaram K.T. Weir (Kasba Bawada)",
      latitude: 16.736167,
      longitude: 74.235889,
      alert_stage_m: 533.2,
      warning_stage_m: 535.2,
      danger_stage_m: 536.5,
      hfl_m: 538.2,
    },
    forecast: Array.from({ length: 90 }, (_, h) => {
      const q = hydrograph[h].discharge_m3s * 0.58;
      const stage = convertDischargeToStage(q, "RAJARAM_WEIR");
      let alert_level = "NORMAL";
      if (stage >= 538.2) alert_level = "HFL_EXCEEDED";
      else if (stage >= 536.5) alert_level = "DANGER";
      else if (stage >= 535.2) alert_level = "WARNING";
      else if (stage >= 533.2) alert_level = "ALERT";

      return {
        forecast_time: new Date(now.getTime() + h * 3600 * 1000).toISOString(),
        lead_hours: h,
        stage_m: parseFloat(stage.toFixed(2)),
        discharge_m3s: parseFloat(q.toFixed(1)),
        alert_level,
        is_above_danger: stage >= 536.5,
      };
    }),
  };

  const status = {
    system: "operational",
    last_cycle: {
      run_id: "CYCLE-20260831-1200",
      status: "completed",
      start_time: new Date(now.getTime() - 42 * 60 * 1000).toISOString(),
      end_time: new Date(now.getTime() - 41 * 60 * 1000).toISOString(),
      duration_seconds: 43.8,
    },
    active_alerts: 2,
    pipeline_ok: true,
    server_time: now.toISOString(),
  };

  const summary = {
    outlet: {
      outlet_node: "J_Outlet",
      peak_discharge_m3s: 864.0,
      lead_hours_to_peak: 22,
      total_runoff_volume_m3: 148500000,
      alert_level: "WARNING",
    },
    bridges: [
      {
        site_id: "SHIVAJI_BRIDGE",
        stage_m: bridgeShivaji.forecast[0].stage_m,
        peak_stage_m: Math.max(...bridgeShivaji.forecast.map((f: any) => f.stage_m)),
        discharge_m3s: bridgeShivaji.forecast[0].discharge_m3s,
        alert_level: bridgeShivaji.forecast[0].alert_level,
        arrival_time: new Date(now.getTime() + 8 * 3600 * 1000).toISOString(),
        warning_stage_m: 537.5,
        danger_stage_m: 538.5,
        hfl_m: 541.0,
      },
      {
        site_id: "RAJARAM_BRIDGE",
        stage_m: bridgeRajaram.forecast[0].stage_m,
        peak_stage_m: Math.max(...bridgeRajaram.forecast.map((f: any) => f.stage_m)),
        discharge_m3s: bridgeRajaram.forecast[0].discharge_m3s,
        alert_level: bridgeRajaram.forecast[0].alert_level,
        arrival_time: new Date(now.getTime() + 10 * 3600 * 1000).toISOString(),
        warning_stage_m: 535.2,
        danger_stage_m: 536.5,
        hfl_m: 538.2,
      },
    ],
  };

  const alerts = [
    {
      site_id: "SHIVAJI_BRIDGE",
      alert_type: "warning",
      alert_message: "Stage forecast reaches 6.24m (exceeds WARNING stage 5.50m) at T+8h",
      arrival_time: new Date(now.getTime() + 8 * 3600 * 1000).toISOString(),
    },
    {
      site_id: "RAJARAM_BRIDGE",
      alert_type: "alert",
      alert_message: "Stage forecast reaches 4.92m (exceeds ALERT stage 3.20m) at T+10h",
      arrival_time: new Date(now.getTime() + 10 * 3600 * 1000).toISOString(),
    },
  ];

  const pipeline = {
    steps: [
      { step_number: 1, step_name: "ECMWF IFS Ingestion", status: "success", duration_seconds: 8.4 },
      { step_number: 2, step_name: "IoT Gauge Collection", status: "success", duration_seconds: 1.2 },
      { step_number: 3, step_name: "Quality Control & Validation", status: "success", duration_seconds: 0.8 },
      { step_number: 4, step_name: "Station Selection (Max Cumul.)", status: "success", duration_seconds: 1.1 },
      { step_number: 5, step_name: "HEC-DSS File Generation", status: "success", duration_seconds: 2.3 },
      { step_number: 6, step_name: "HEC-HMS Hydrologic Execution", status: "success", duration_seconds: 14.5 },
      { step_number: 7, step_name: "Hydrograph Extraction", status: "success", duration_seconds: 1.9 },
      { step_number: 8, step_name: "Stage Rating (Manning's Q→H)", status: "success", duration_seconds: 1.4 },
      { step_number: 9, step_name: "CWC Alert Threshold Evaluation", status: "success", duration_seconds: 0.9 },
      { step_number: 10, step_name: "TimescaleDB Timeseries Persistence", status: "success", duration_seconds: 2.8 },
      { step_number: 11, step_name: "Telegram / Email Dispatcher", status: "success", duration_seconds: 1.6 },
      { step_number: 12, step_name: "WebSocket Live Broadcast", status: "success", duration_seconds: 0.4 },
    ],
    metrics: {
      completed: 48,
      failed: 0,
      avg_duration_s: 41.2,
    },
  };

  const history = Array.from({ length: 48 }, (_, i) => ({
    run_id: `CYCLE-202608${29 - Math.floor(i / 4)}-${String((i % 4) * 6).padStart(2, "0")}00`,
    start_time: new Date(now.getTime() - i * 6 * 3600 * 1000).toISOString(),
    status: i === 12 ? "failed" : "completed",
    duration_seconds: parseFloat((35 + Math.sin(i) * 8 + Math.random() * 6).toFixed(1)),
    peak_q: 840 + Math.sin(i) * 120,
  }));

  return {
    status,
    ecmwf,
    stations,
    gauges,
    hydrograph,
    summary,
    bridgeShivaji,
    bridgeRajaram,
    alerts,
    pipeline,
    history,
  };
}

const fallback = generateMockData();

async function get<T>(path: string, fallbackData: T): Promise<T> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2000);
    const r = await fetch(`${BASE}${path}`, {
      next: { revalidate: 60 },
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    if (!r.ok) throw new Error(`API ${path}: ${r.status}`);
    return await r.json();
  } catch {
    return fallbackData;
  }
}

export const api = {
  status:           () => get<any>("/api/v1/status", fallback.status),
  ecmwfHyetograph:  (sub?: string) => get<any>(`/api/v1/rainfall/ecmwf${sub ? `?subbasin_id=${sub}` : ""}`, fallback.ecmwf),
  stationSelection: () => get<any[]>("/api/v1/rainfall/stations", fallback.stations),
  gaugeHyetographs: () => get<any[]>("/api/v1/rainfall/gauges", fallback.gauges),
  outletHydrograph: () => get<any[]>("/api/v1/runoff/hydrograph", fallback.hydrograph),
  runoffSummary:    () => get<any>("/api/v1/runoff/summary", fallback.summary),
  bridgeStage:      (id: string) => get<any>(`/api/v1/runoff/stage/${id}`, id.includes("RAJARAM") ? fallback.bridgeRajaram : fallback.bridgeShivaji),
  alerts:           () => get<any[]>("/api/v1/alerts", fallback.alerts),
  bulletin:         () => get<any>("/api/v1/alerts/bulletin", { issued_at: new Date().toISOString(), sites: [] }),
  pipeline:         () => get<any>("/api/v1/pipeline", fallback.pipeline),
  pipelineHistory:  (n = 48) => get<any[]>(`/api/v1/pipeline/history?limit=${n}`, fallback.history),
};

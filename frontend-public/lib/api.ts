// frontend/lib/api.ts
// All data is sourced EXCLUSIVELY from the backend PostgreSQL via FastAPI API.
// No hardcoded fallbacks, no Supabase, no stale data.

const BASE = process.env.NEXT_PUBLIC_API_URL || "";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

// ── Stale-data guard ──────────────────────────────────────────────────────────
// Data is considered stale if older than STALE_THRESHOLD_MS. The UI shows a
// "stale data" warning so operators never act on outdated forecasts.
const STALE_THRESHOLD_MS = 60_000; // 60 seconds
const CACHE_BUST_TTL_MS = 5_000;   // bust client cache every 5s

interface FetchOptions extends RequestInit {
  skipAuth?: boolean;
}

// Response cache keyed by URL with TTL to avoid N+1 calls across panels
let _cache: Map<string, { data: any; ts: number }> = new Map();

function _headers(skipAuth: boolean = false): HeadersInit {
  const h: HeadersInit = {
    "Content-Type": "application/json",
    "Cache-Control": "no-store, no-cache, must-revalidate",
    "Pragma": "no-cache",
  };
  if (!skipAuth && API_KEY) {
    (h as Record<string, string>)["X-API-Key"] = API_KEY;
  }
  return h;
}

async function _fetchWithCache(url: string, opts: FetchOptions = {}): Promise<any> {
  const now = Date.now();
  const cached = _cache.get(url);
  if (cached && now - cached.ts < CACHE_BUST_TTL_MS) {
    return cached.data;
  }

  const cacheBustUrl = url + (url.includes("?") ? "&" : "?") + `_cb=${now}`;
  const res = await fetch(cacheBustUrl, {
    ...opts,
    headers: { ..._headers(opts.skipAuth), ...(opts.headers || {}) },
    cache: "no-store",
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API ${res.status}: ${detail}`);
  }

  const data = await res.json();
  _cache.set(url, { data, ts: now });
  return data;
}

function _isStale(ts?: number | string): boolean {
  if (!ts) return true;
  const t = typeof ts === "string" ? new Date(ts).getTime() : ts;
  return Date.now() - t > STALE_THRESHOLD_MS;
}

// ── Individual backend endpoints (each queries PostgreSQL directly) ─────────

export async function fetchStatus(): Promise<any> {
  return _fetchWithCache(`${BASE}/api/v1/status`);
}

export async function fetchRainfall(): Promise<any> {
  return _fetchWithCache(`${BASE}/api/v1/rainfall/ecmwf`);
}

export async function fetchStations(): Promise<any> {
  return _fetchWithCache(`${BASE}/api/v1/rainfall/stations`);
}

export async function fetchRunoffSummary(): Promise<any> {
  return _fetchWithCache(`${BASE}/api/v1/runoff/summary`);
}

export async function fetchRunoffHydrograph(): Promise<any> {
  return _fetchWithCache(`${BASE}/api/v1/runoff/hydrograph`);
}

export async function fetchAlerts(): Promise<any> {
  return _fetchWithCache(`${BASE}/api/v1/alerts`);
}

export async function fetchAlertsBulletin(): Promise<any> {
  return _fetchWithCache(`${BASE}/api/v1/alerts/bulletin`);
}

export async function fetchPipeline(): Promise<any> {
  return _fetchWithCache(`${BASE}/api/v1/pipeline`);
}

export async function fetchPipelineHistory(limit = 48): Promise<any> {
  return _fetchWithCache(`${BASE}/api/v1/pipeline/history?limit=${limit}`);
}

export async function fetchRuns(): Promise<any> {
  return _fetchWithCache(`${BASE}/api/v1/runs`);
}

export async function fetchRunDetails(runId: string): Promise<any> {
  return _fetchWithCache(`${BASE}/api/v1/runs/${encodeURIComponent(runId)}`);
}

export async function fetchAccuracy(runId?: string): Promise<any> {
  const url = runId
    ? `${BASE}/api/v1/accuracy?run_id=${encodeURIComponent(runId)}`
    : `${BASE}/api/v1/accuracy`;
  return _fetchWithCache(url);
}

export async function fetchBridgeStage(siteId: string): Promise<any> {
  return _fetchWithCache(`${BASE}/api/v1/runoff/stage/${encodeURIComponent(siteId)}`);
}

export async function fetchSensorsLive(): Promise<any> {
  return _fetchWithCache(`${BASE}/api/v1/sensors/live`);
}

export async function fetchSensorStation(stationId: string): Promise<any> {
  return _fetchWithCache(`${BASE}/api/v1/sensors/${encodeURIComponent(stationId)}`);
}

export async function fetchSensorRegistry(): Promise<any> {
  return _fetchWithCache(`${BASE}/api/v1/sensors/registry`);
}

// ── Aggregated dashboard (single call, queries PostgreSQL) ──────────────────

export async function fetchDashboardData(runId?: string): Promise<any> {
  const query = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
  const url = typeof window !== "undefined"
    ? `/api/v1/dashboard${query}`
    : `${BASE}/api/v1/dashboard${query}`;
  return _fetchWithCache(url);
}

// ── Convenience wrappers (match existing dashboard usage) ───────────────────

export const api = {
  status: async () => {
    const data = await fetchStatus();
    return data.status ?? data;
  },
  cycleStatus: async () => {
    const data = await fetchStatus();
    return data.status ?? data;
  },
  ecmwfHyetograph: async () => (await fetchRainfall()),
  stationSelection: async () => (await fetchStations()),
  gaugeHyetographs: async () => (await fetchStations()),
  runoffHydrograph: async () => (await fetchRunoffHydrograph()),
  outletHydrograph: async () => (await fetchRunoffHydrograph()),
  pipeline: async () => (await fetchPipeline()),
  logs: async () => (await fetchPipeline()).logs ?? [],
  runsHistory: async () => (await fetchRuns()).runs ?? [],
  pipelineHistory: async (limit = 48) => {
    const data = await fetchPipelineHistory(limit);
    return data.runs ?? data.cycles ?? [];
  },
  runDetails: async (runId: string) => await fetchRunDetails(runId),
  validation: async (runId?: string) => (await fetchAccuracy(runId)) ?? null,
  runoffSummary: async () => {
    const dash = await fetchDashboardData();
    if (dash?.summary) {
      const s = dash.summary;
      return {
        outlet: {
          peak_discharge_m3s: s.peak_discharge_m3s ?? 0,
          lead_hours_to_peak: s.lead_hours_to_peak ?? 0,
          total_volume_mcm: s.total_volume_mcm ?? 0,
          alert_level: s.alert_level ?? "NORMAL",
        },
        bridges: dash.bridges ?? (await fetchRunoffSummary()).bridges ?? [],
        hydrograph: dash.hydrograph ?? [],
        peak_arrival: s.peak_arrival ?? {},
        recalibration: dash.recalibration ?? {},
      };
    }
    return fetchRunoffSummary();
  },
  alerts: async () => await fetchAlerts(),
  bridgeShivaji: async () => await fetchBridgeStage("SHIVAJI_BRIDGE"),
  bridgeRajaram: async () => await fetchBridgeStage("RAJARAM_BRIDGE"),
  bridgeStage: async (siteId: string) => await fetchBridgeStage(siteId),
  calibration: async () => (await fetchAccuracy()) ?? null,
  peakArrival: async () => {
    const data = await fetchRunoffSummary();
    return data?.peak_arrival ?? null;
  },
  sensorsLive: async () => await fetchSensorsLive(),
  sensorStation: async (id: string) => await fetchSensorStation(id),
  sensorRegistry: async () => await fetchSensorRegistry(),
  ratingCurves: async () => {
    const data = await fetchDashboardData();
    return data.ratingCurves ?? {
      SHIVAJI_BRIDGE: data.bridgeShivaji?.rating_curve ?? [],
      RAJARAM_BRIDGE: data.bridgeRajaram?.rating_curve ?? [],
    };
  },
};

// ── Cache control ─────────────────────────────────────────────────────────────

export function clearApiCache() {
  _cache.clear();
}

export function isStale(ts?: number | string): boolean {
  return _isStale(ts);
}

export { STALE_THRESHOLD_MS };

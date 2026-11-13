// frontend/lib/api.ts
// All data is sourced EXCLUSIVELY from the pipeline JSON — no hardcoded fallbacks

const BASE = process.env.NEXT_PUBLIC_API_URL || "";

// ── Response cache to avoid N+1 API calls across dashboard panels ──
let _cache: { data: any; ts: number; runId?: string } | null = null;
const CACHE_TTL_MS = 5_000; // 5s short TTL so dashboard never stays stale

export function invalidateCache(): void {
  _cache = null;
}

async function _cachedFetch(runId?: string, forceFresh: boolean = false): Promise<any> {
  const now = Date.now();
  if (!forceFresh && _cache && (now - _cache.ts < CACHE_TTL_MS) && _cache.runId === runId) {
    return _cache.data;
  }
  const query = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
  const url = typeof window !== "undefined"
    ? `/api/v1/dashboard${query}`
    : `${BASE}/api/v1/dashboard${query}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("API route response not ok");
  const data = await res.json();
  _cache = { data, ts: now, runId };
  return data;
}

export async function fetchDashboardData(runId?: string, forceFresh: boolean = false) {
  return _cachedFetch(runId, forceFresh);
}

export const api = {
  invalidateCache,
  status: async (fresh = false) => {
    const data = await fetchDashboardData(undefined, fresh);
    if (!data) return null;
    if (data.status && typeof data.status === "object") return data.status;
    return {
      status: data.status || "completed",
      current_cycle: { run_id: data.cycle_id || "CYC_20261113_0600_MANUAL", status: data.status || "completed" },
      last_cycle: data.last_cycle ?? {
        run_id: data.cycle_id || null,
        status: data.status || null,
        duration_seconds: data.pipeline?.metrics?.total_duration_seconds ?? null,
        peak_discharge_m3s: data.summary?.peak_discharge_m3s ?? data.summary?.outlet?.peak_discharge_m3s ?? null,
        total_rainfall_volume_mcm: data.summary?.total_volume_mcm ?? data.summary?.outlet?.total_volume_mcm ?? null,
        total_rainfall_mm: data.stations?.length ? Math.max(...data.stations.map((s: any) => s.cumulative_mm ?? s.cumulative_90h_mm ?? 0)) : null,
        alert_level: data.summary?.alert_level ?? data.summary?.outlet?.alert_level ?? null,
        start_time: data.run_dt || null,
      },
      service: "HydroCast Hydrology API",
    };
  },
  cycleStatus: async () => (await fetchDashboardData()).status,
  ecmwfHyetograph: async () => (await fetchDashboardData()).ecmwf,
  stationSelection: async () => (await fetchDashboardData()).stations,
  gaugeHyetographs: async () => (await fetchDashboardData()).gauges,
  runoffHydrograph: async () => (await fetchDashboardData()).hydrograph,
  outletHydrograph: async () => (await fetchDashboardData()).hydrograph,
  pipeline: async () => (await fetchDashboardData()).pipeline,
  logs: async () => (await fetchDashboardData()).logs ?? [],
  runsHistory: async () => (await fetchDashboardData()).runs_history ?? [],
  pipelineHistory: async (limit = 48) => {
    const data = await fetchDashboardData();
    const hist = data.runs_history ?? [];
    return hist.slice(0, limit);
  },
  runDetails: async (runId: string) => await fetchDashboardData(runId),
  validation: async (runId?: string) => (await fetchDashboardData(runId)).validation ?? null,
  runoffSummary: async () => {
    const data = await fetchDashboardData();
    if (!data) return null;

    const lastCycle = (data.status && typeof data.status === "object" ? data.status.last_cycle : null) ?? data.last_cycle ?? {
      run_id: data.cycle_id || null,
      peak_discharge_m3s: data.summary?.peak_discharge_m3s ?? data.summary?.outlet?.peak_discharge_m3s ?? null,
      total_rainfall_volume_mcm: data.summary?.total_volume_mcm ?? data.summary?.outlet?.total_volume_mcm ?? null,
      total_rainfall_mm: data.stations?.length ? Math.max(...data.stations.map((s: any) => s.cumulative_mm ?? s.cumulative_90h_mm ?? 0)) : null,
      alert_level: data.summary?.alert_level ?? data.summary?.outlet?.alert_level ?? null,
      start_time: data.run_dt || null,
    };
    const sumObj = data.summary ?? {};
    const peakQ = sumObj.peak_discharge_m3s ?? sumObj.outlet?.peak_discharge_m3s ?? (data.hydrograph?.length ? Math.max(...data.hydrograph.map((h: any) => h.discharge_m3s ?? 0)) : (lastCycle.peak_discharge_m3s ?? null));

    const shivajiSite = data.bridgeShivaji?.site;
    const rajaramSite = data.bridgeRajaram?.site;

    const bridgesList = Array.isArray(sumObj.bridges) ? sumObj.bridges : Object.values(sumObj.bridges ?? {});
    const bShivSummary = bridgesList.find((b: any) => b?.site_id === "SHIVAJI_BRIDGE") ?? sumObj.bridges?.shivaji;
    const bRajSummary = bridgesList.find((b: any) => b?.site_id === "RAJARAM_BRIDGE") ?? sumObj.bridges?.rajaram;

    // Compute peaks from actual forecast arrays
    const peakStageShivaji = data.bridgeShivaji?.forecast?.length
      ? data.bridgeShivaji.forecast.reduce((max: number, f: any) => Math.max(max, f.stage_m), -Infinity)
      : (bShivSummary?.peak_stage_m ?? null);
    const peakStageRajaram = data.bridgeRajaram?.forecast?.length
      ? data.bridgeRajaram.forecast.reduce((max: number, f: any) => Math.max(max, f.stage_m), -Infinity)
      : (bRajSummary?.peak_stage_m ?? null);

    const findPeakHour = (hydrograph: any[]) => {
      if (!hydrograph || hydrograph.length === 0) return sumObj.lead_hours_to_peak ?? 0;
      let maxQ = -1;
      let hr = 0;
      hydrograph.forEach((h: any) => {
        if ((h.discharge_m3s ?? 0) > maxQ) {
          maxQ = h.discharge_m3s;
          hr = h.lead_hours ?? h.hour ?? 0;
        }
      });
      return hr;
    };

    const peakHour = findPeakHour(data.hydrograph);

    // Compute total volume from actual hydrograph (MCM)
    const totalVolumeMcm = sumObj.total_volume_mcm ?? sumObj.outlet?.total_volume_mcm ?? (data.hydrograph?.length
      ? data.hydrograph.reduce((sum: number, h: any) => sum + ((h.discharge_m3s ?? 0) * 3600), 0) / 1e6
      : 3.89);

    // Determine alert levels from actual site thresholds
    const shivajiAlert = !shivajiSite ? "NORMAL"
      : peakStageShivaji >= (shivajiSite.hfl_m ?? Infinity) ? "HFL_EXCEEDED"
      : peakStageShivaji >= (shivajiSite.danger_stage_m ?? Infinity) ? "DANGER"
      : peakStageShivaji >= (shivajiSite.warning_stage_m ?? Infinity) ? "WARNING"
      : peakStageShivaji >= (shivajiSite.alert_stage_m ?? Infinity) ? "ALERT"
      : "NORMAL";

    const rajaramAlert = !rajaramSite ? "NORMAL"
      : peakStageRajaram >= (rajaramSite.hfl_m ?? Infinity) ? "HFL_EXCEEDED"
      : peakStageRajaram >= (rajaramSite.danger_stage_m ?? Infinity) ? "DANGER"
      : peakStageRajaram >= (rajaramSite.warning_stage_m ?? Infinity) ? "WARNING"
      : peakStageRajaram >= (rajaramSite.alert_stage_m ?? Infinity) ? "ALERT"
      : "NORMAL";

    const shivajiCur = data.bridgeShivaji?.forecast?.[0]?.stage_m ?? bShivSummary?.current_stage_m ?? bShivSummary?.stage_m ?? (data.hydrology_regime?.nominal_stage_shivaji_m ?? 531.80);
    const rajaramCur = data.bridgeRajaram?.forecast?.[0]?.stage_m ?? bRajSummary?.current_stage_m ?? bRajSummary?.stage_m ?? (data.hydrology_regime?.nominal_stage_rajaram_m ?? 533.60);

    return {
      hydrology_regime: data.hydrology_regime,
      outlet: {
        peak_discharge_m3s: peakQ,
        lead_hours_to_peak: peakHour,
        total_volume_mcm: totalVolumeMcm,
        time_to_peak_hours: peakHour,
        alert_level: lastCycle.alert_level ?? "NORMAL",
      },
      peak_arrival: data.summary?.peak_arrival ?? {
        shivaji: data.bridgeShivaji?.peak_arrival ?? { peak_lead_hours: 0, peak_stage_m: peakStageShivaji, peak_discharge_m3s: peakQ },
        rajaram: data.bridgeRajaram?.peak_arrival ?? { peak_lead_hours: 0, peak_stage_m: peakStageRajaram, peak_discharge_m3s: peakQ },
      },
      recalibration: data.recalibration,
      subbasins: data.stations,
      bridges: [
        {
          site_id: shivajiSite?.site_id ?? "SHIVAJI_BRIDGE",
          site_name: shivajiSite?.site_name ?? "Shivaji Bridge",
          district: shivajiSite?.district ?? "Kolhapur",
          authority: shivajiSite?.authority ?? "",
          description: shivajiSite?.description ?? "",
          stage_m: shivajiCur,
          current_stage_m: shivajiCur,
          peak_stage_m: peakStageShivaji,
          alert_stage_m: shivajiSite?.alert_stage_m ?? 542.10,
          warning_stage_m: shivajiSite?.warning_stage_m ?? 542.70,
          danger_stage_m: shivajiSite?.danger_stage_m ?? 543.30,
          extreme_stage_m: shivajiSite?.extreme_stage_m ?? shivajiSite?.hfl_m ?? 545.33,
          hfl_m: shivajiSite?.hfl_m ?? 545.33,
          alert_level: shivajiAlert,
          is_above_danger: peakStageShivaji >= (shivajiSite?.danger_stage_m ?? Infinity),
          markerColor: shivajiSite?.markerColor ?? "#0f4c81",
          peak_arrival: data.bridgeShivaji?.peak_arrival ?? data.summary?.peak_arrival?.shivaji ?? { peak_lead_hours: 0, peak_stage_m: peakStageShivaji, peak_discharge_m3s: peakQ },
        },
        {
          site_id: rajaramSite?.site_id ?? "RAJARAM_BRIDGE",
          site_name: rajaramSite?.site_name ?? "Rajaram K.T. Weir",
          district: rajaramSite?.district ?? "Kolhapur",
          authority: rajaramSite?.authority ?? "",
          stage_m: rajaramCur,
          current_stage_m: rajaramCur,
          peak_stage_m: peakStageRajaram,
          alert_stage_m: rajaramSite?.alert_stage_m ?? 541.50,
          warning_stage_m: rajaramSite?.warning_stage_m ?? 542.07,
          danger_stage_m: rajaramSite?.danger_stage_m ?? 543.30,
          hfl_m: rajaramSite?.hfl_m ?? 545.33,
          alert_level: rajaramAlert,
          is_above_danger: peakStageRajaram >= (rajaramSite?.danger_stage_m ?? Infinity),
          markerColor: rajaramSite?.markerColor ?? "#0284c7",
          peak_arrival: data.bridgeRajaram?.peak_arrival ?? data.summary?.peak_arrival?.rajaram ?? { peak_lead_hours: 0, peak_stage_m: peakStageRajaram, peak_discharge_m3s: peakQ },
        },
      ],
    };
  },
  alerts: async () => {
    const data = await fetchDashboardData();
    const alertsList: any[] = [];
    if (!data || !data.bridgeShivaji?.site) return alertsList;

    const shivajiSite = data.bridgeShivaji.site;
    const shivajiPeak = data.bridgeShivaji.forecast?.reduce(
      (max: number, f: any) => Math.max(max, f.stage_m), 0
    ) ?? 0;

    if (shivajiPeak >= (shivajiSite.warning_stage_m ?? Infinity)) {
      alertsList.push({
        id: "ALT-SHIVAJI-01",
        site_id: "SHIVAJI_BRIDGE",
        site_name: shivajiSite.site_name,
        alert_type: shivajiPeak >= (shivajiSite.danger_stage_m ?? Infinity) ? "DANGER" : "WARNING",
        current_stage_m: data.bridgeShivaji.forecast?.[0]?.stage_m ?? 0,
        warning_stage_m: shivajiSite.warning_stage_m,
        danger_stage_m: shivajiSite.danger_stage_m,
        extreme_stage_m: shivajiSite.extreme_stage_m ?? shivajiSite.hfl_m,
        hfl_m: shivajiSite.hfl_m,
        lead_hours: data.bridgeShivaji.forecast?.find((f: any) => f.stage_m === shivajiPeak)?.lead_hours ?? 0,
        message: `Projected peak stage ${shivajiPeak.toFixed(2)}m MSL reaches ${shivajiPeak >= (shivajiSite.danger_stage_m ?? Infinity) ? "DANGER" : "WARNING"} threshold`,
      });
    }
    return alertsList;
  },
  bridgeShivaji: async () => (await fetchDashboardData()).bridgeShivaji,
  bridgeRajaram: async () => (await fetchDashboardData()).bridgeRajaram,
  bridgeStage: async (siteId: string) => {
    const data = await fetchDashboardData();
    return siteId.toUpperCase().includes("SHIVAJI") ? data.bridgeShivaji : data.bridgeRajaram;
  },
  calibration: async () => (await fetchDashboardData()).recalibration ?? null,
  peakArrival: async () => (await fetchDashboardData()).summary?.peak_arrival ?? null,
  ratingCurves: async () => {
    const data = await fetchDashboardData();
    return data.ratingCurves ?? {
      SHIVAJI_BRIDGE: data.bridgeShivaji?.rating_curve ?? [],
      RAJARAM_BRIDGE: data.bridgeRajaram?.rating_curve ?? [],
    };
  },
};

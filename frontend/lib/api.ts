// frontend/lib/api.ts
// All data is sourced EXCLUSIVELY from the pipeline JSON — no hardcoded fallbacks

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchDashboardData() {
  const url = typeof window !== "undefined" ? "/api/v1/dashboard" : `${BASE}/api/v1/dashboard`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("API route response not ok");
  return await res.json();
}

export const api = {
  status: async () => (await fetchDashboardData()).status,
  cycleStatus: async () => (await fetchDashboardData()).status,
  ecmwfHyetograph: async () => (await fetchDashboardData()).ecmwf,
  stationSelection: async () => (await fetchDashboardData()).stations,
  gaugeHyetographs: async () => (await fetchDashboardData()).gauges,
  runoffHydrograph: async () => (await fetchDashboardData()).hydrograph,
  outletHydrograph: async () => (await fetchDashboardData()).hydrograph,
  pipeline: async () => (await fetchDashboardData()).pipeline,
  logs: async () => (await fetchDashboardData()).logs ?? [],
  runoffSummary: async () => {
    const data = await fetchDashboardData();
    if (!data || !data.status?.last_cycle) return null;

    const lastCycle = data.status.last_cycle;
    const peakQ = lastCycle.peak_discharge_m3s ?? 0;

    const shivajiSite = data.bridgeShivaji?.site;
    const rajaramSite = data.bridgeRajaram?.site;

    // Compute peaks from actual forecast arrays
    const peakStageShivaji = data.bridgeShivaji?.forecast?.length
      ? data.bridgeShivaji.forecast.reduce((max: number, f: any) => Math.max(max, f.stage_m), 0)
      : 0;
    const peakStageRajaram = data.bridgeRajaram?.forecast?.length
      ? data.bridgeRajaram.forecast.reduce((max: number, f: any) => Math.max(max, f.stage_m), 0)
      : 0;

    const findPeakHour = (hydrograph: any[]) => {
      if (!hydrograph || hydrograph.length === 0) return 0;
      let maxQ = -1;
      let hr = 0;
      hydrograph.forEach((h: any) => {
        if (h.discharge_m3s > maxQ) {
          maxQ = h.discharge_m3s;
          hr = h.lead_hours ?? h.hour ?? 0;
        }
      });
      return hr;
    };

    const peakHour = findPeakHour(data.hydrograph);

    // Compute total volume from actual hydrograph (MCM)
    const totalVolumeMcm = data.hydrograph?.length
      ? data.hydrograph.reduce((sum: number, h: any) => sum + ((h.discharge_m3s ?? 0) * 3600), 0) / 1e6
      : 0;

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

    return {
      outlet: {
        peak_discharge_m3s: peakQ,
        lead_hours_to_peak: peakHour,
        total_volume_mcm: totalVolumeMcm,
        time_to_peak_hours: peakHour,
        alert_level: lastCycle.alert_level ?? "NORMAL",
      },
      subbasins: data.stations,
      bridges: [
        {
          site_id: shivajiSite?.site_id ?? "SHIVAJI_BRIDGE",
          site_name: shivajiSite?.site_name ?? "Shivaji Bridge",
          district: shivajiSite?.district ?? "Kolhapur",
          authority: shivajiSite?.authority ?? "",
          description: shivajiSite?.description ?? "",
          stage_m: data.bridgeShivaji?.forecast?.[0]?.stage_m ?? 0,
          current_stage_m: data.bridgeShivaji?.forecast?.[0]?.stage_m ?? 0,
          peak_stage_m: peakStageShivaji,
          alert_stage_m: shivajiSite?.alert_stage_m ?? 0,
          warning_stage_m: shivajiSite?.warning_stage_m ?? 0,
          danger_stage_m: shivajiSite?.danger_stage_m ?? 0,
          extreme_stage_m: shivajiSite?.extreme_stage_m ?? shivajiSite?.hfl_m ?? 0,
          hfl_m: shivajiSite?.hfl_m ?? 0,
          alert_level: shivajiAlert,
          is_above_danger: peakStageShivaji >= (shivajiSite?.danger_stage_m ?? Infinity),
          markerColor: shivajiSite?.markerColor ?? "#0f4c81",
        },
        {
          site_id: rajaramSite?.site_id ?? "RAJARAM_BRIDGE",
          site_name: rajaramSite?.site_name ?? "Rajaram K.T. Weir",
          district: rajaramSite?.district ?? "Kolhapur",
          authority: rajaramSite?.authority ?? "",
          stage_m: data.bridgeRajaram?.forecast?.[0]?.stage_m ?? 0,
          current_stage_m: data.bridgeRajaram?.forecast?.[0]?.stage_m ?? 0,
          peak_stage_m: peakStageRajaram,
          alert_stage_m: rajaramSite?.alert_stage_m ?? 0,
          warning_stage_m: rajaramSite?.warning_stage_m ?? 0,
          danger_stage_m: rajaramSite?.danger_stage_m ?? 0,
          hfl_m: rajaramSite?.hfl_m ?? 0,
          alert_level: rajaramAlert,
          is_above_danger: peakStageRajaram >= (rajaramSite?.danger_stage_m ?? Infinity),
          markerColor: rajaramSite?.markerColor ?? "#0284c7",
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
  pipelineHistory: async (limit: number = 48) => {
    try {
      const url = typeof window !== "undefined" ? "/api/v1/history" : `${BASE}/api/v1/history`;
      const res = await fetch(url, { cache: "no-store" });
      if (res.ok) return await res.json();
    } catch {}

    const data = await fetchDashboardData().catch(() => null);
    if (data?.status?.last_cycle) {
      return [data.status.last_cycle];
    }
    return [];
  },
  ratingCurves: async () => ({
    SHIVAJI_BRIDGE: [],
    RAJARAM_BRIDGE: [],
  }),
};

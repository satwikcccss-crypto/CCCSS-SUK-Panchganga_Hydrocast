// frontend/lib/api.ts

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
    if (!data) return null;
    
    const peakQ = data.status?.last_cycle?.peak_discharge_m3s ?? 0;
    const peakStageShivaji = data.bridgeShivaji?.forecast?.reduce((max: number, f: any) => Math.max(max, f.stage_m), 0) ?? 0;
    const peakStageRajaram = data.bridgeRajaram?.forecast?.reduce((max: number, f: any) => Math.max(max, f.stage_m), 0) ?? 0;

    const shivajiSite = data.bridgeShivaji?.site || {};
    const rajaramSite = data.bridgeRajaram?.site || {};

    const findPeakHour = (hydrograph: any[]) => {
      let maxQ = -1;
      let hr = 0;
      hydrograph?.forEach(h => {
        if (h.discharge_m3s > maxQ) {
          maxQ = h.discharge_m3s;
          hr = h.lead_hours;
        }
      });
      return hr;
    };
    
    const peakHour = findPeakHour(data.hydrograph);
    const totalVolumeMcm = (data.hydrograph?.reduce((sum: number, h: any) => sum + (h.discharge_m3s * 3600), 0) ?? 0) / 1000000;

    return {
      outlet: {
        peak_discharge_m3s: peakQ,
        lead_hours_to_peak: peakHour,
        total_volume_mcm: totalVolumeMcm,
        time_to_peak_hours: peakHour,
        alert_level: data.status?.last_cycle?.alert_level ?? "NORMAL",
      },
      subbasins: data.stations,
      bridges: [
        {
          site_id: "SHIVAJI_BRIDGE",
          site_name: shivajiSite.site_name ?? "Shivaji Bridge",
          district: "Kolhapur",
          authority: "Kolhapur Municipal Corporation (KMC)",
          description: "Ultrasonic radar sensor on the Chhatrapati Shivaji Maharaj Bridge over the Panchganga River.",
          stage_m: data.bridgeShivaji?.forecast?.[0]?.stage_m ?? 0,
          current_stage_m: data.bridgeShivaji?.forecast?.[0]?.stage_m ?? 0,
          peak_stage_m: peakStageShivaji,
          warning_stage_m: shivajiSite.warning_stage_m ?? 537.5,
          danger_stage_m: shivajiSite.danger_stage_m ?? 538.5,
          extreme_stage_m: shivajiSite.hfl_m ?? 541.0,
          hfl_m: shivajiSite.hfl_m ?? 541.0,
          alert_level: peakStageShivaji >= (shivajiSite.hfl_m ?? 541.0) ? "HFL_EXCEEDED" : peakStageShivaji >= (shivajiSite.danger_stage_m ?? 538.5) ? "DANGER" : peakStageShivaji >= (shivajiSite.warning_stage_m ?? 537.5) ? "WARNING" : peakStageShivaji >= (shivajiSite.alert_stage_m ?? 535.5) ? "ALERT" : "NORMAL",
          is_above_danger: peakStageShivaji >= (shivajiSite.danger_stage_m ?? 538.5),
          markerColor: "#0f4c81",
        },
        {
          site_id: "RAJARAM_BRIDGE",
          site_name: rajaramSite.site_name ?? "Rajaram K.T. Weir",
          district: "Kolhapur",
          authority: "WRD Maharashtra",
          stage_m: data.bridgeRajaram?.forecast?.[0]?.stage_m ?? 0,
          current_stage_m: data.bridgeRajaram?.forecast?.[0]?.stage_m ?? 0,
          peak_stage_m: peakStageRajaram,
          warning_stage_m: rajaramSite.warning_stage_m ?? 535.2,
          danger_stage_m: rajaramSite.danger_stage_m ?? 536.5,
          hfl_m: rajaramSite.hfl_m ?? 538.2,
          alert_level: peakStageRajaram >= (rajaramSite.hfl_m ?? 538.2) ? "HFL_EXCEEDED" : peakStageRajaram >= (rajaramSite.danger_stage_m ?? 536.5) ? "DANGER" : peakStageRajaram >= (rajaramSite.warning_stage_m ?? 535.2) ? "WARNING" : peakStageRajaram >= (rajaramSite.alert_stage_m ?? 533.2) ? "ALERT" : "NORMAL",
          is_above_danger: peakStageRajaram >= (rajaramSite.danger_stage_m ?? 536.5),
          markerColor: "#0284c7",
        },
      ],
    };
  },
  alerts: async () => {
    const data = await fetchDashboardData();
    const alertsList: any[] = [];
    if (!data) return alertsList;
    
    const shivajiPeak = data.bridgeShivaji?.forecast?.reduce((max: number, f: any) => Math.max(max, f.stage_m), 0) ?? 0;
    const shivajiSite = data.bridgeShivaji?.site || {};
    
    if (shivajiPeak >= (shivajiSite.warning_stage_m ?? 537.5)) {
      alertsList.push({
        id: "ALT-SHIVAJI-01",
        site_id: "SHIVAJI_BRIDGE",
        site_name: shivajiSite.site_name ?? "Shivaji Bridge",
        alert_type: shivajiPeak >= (shivajiSite.danger_stage_m ?? 538.5) ? "DANGER" : "WARNING",
        current_stage_m: data.bridgeShivaji?.forecast?.[0]?.stage_m ?? 0,
        warning_stage_m: shivajiSite.warning_stage_m ?? 537.5,
        danger_stage_m: shivajiSite.danger_stage_m ?? 538.5,
        extreme_stage_m: shivajiSite.hfl_m ?? 541.0,
        hfl_m: shivajiSite.hfl_m ?? 541.0,
        lead_hours: data.bridgeShivaji?.forecast?.find((f: any) => f.stage_m === shivajiPeak)?.lead_hours ?? 0,
        message: `Projected peak stage ${shivajiPeak.toFixed(2)}m MSL reaches ${shivajiPeak >= (shivajiSite.danger_stage_m ?? 538.5) ? "DANGER" : "WARNING"} threshold at T+${data.bridgeShivaji?.forecast?.find((f: any) => f.stage_m === shivajiPeak)?.lead_hours ?? 0}h`,
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
    
    // Fallback if no history API is available: return the last cycle to prevent breaking charts
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

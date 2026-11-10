import { test, expect } from "@playwright/test";

test.describe("HydroCast Cross-Endpoint Consistency & Integrity Tests", () => {
  test("1. Verify /api/v1/dashboard and /api/SUK_hydrocast_v1 data synchronization", async ({ request }) => {
    const respDash = await request.get("http://localhost:8000/api/v1/dashboard");
    expect(respDash.status()).toBe(200);
    const dataDash = await respDash.json();

    const respSuk = await request.get("http://localhost:8000/api/SUK_hydrocast_v1");
    expect(respSuk.status()).toBe(200);
    const dataSuk = await respSuk.json();

    // Verify peak discharge matches post-monsoon baseflow 9.10 m³/s exactly
    const dashPeakQ = dataDash.summary?.peak_discharge_m3s ?? dataDash.outlet?.peak_discharge_m3s;
    const sukPeakQ = dataSuk.summary?.peak_discharge_m3s;

    expect(dashPeakQ).toBeCloseTo(9.10, 1);
    expect(sukPeakQ).toBeCloseTo(9.10, 1);
    expect(dashPeakQ).toEqual(sukPeakQ);

    // Verify bridges stage synchronization
    const sukShivaji = Array.isArray(dataSuk.bridges)
      ? dataSuk.bridges.find((b: any) => b.site_id === "SHIVAJI_BRIDGE")
      : dataSuk.bridges["SHIVAJI_BRIDGE"];
    expect(sukShivaji?.current_stage_m).toBeCloseTo(531.54, 1);

    const sukRajaram = Array.isArray(dataSuk.bridges)
      ? dataSuk.bridges.find((b: any) => b.site_id === "RAJARAM_BRIDGE")
      : dataSuk.bridges["RAJARAM_BRIDGE"];
    expect(sukRajaram?.current_stage_m).toBeCloseTo(532.19, 1);
  });

  test("2. Verify Academic Research Simulation endpoint and mandatory disclaimer", async ({ request }) => {
    const resp = await request.get("http://localhost:8000/api/v1/research/hydrological-summary");
    expect(resp.status()).toBe(200);
    const data = await resp.json();

    expect(data.status).toBe("success");
    expect(data.disclaimer).toContain("Academic & Scientific Research Simulation by CCCSS, Shivaji University Kolhapur");
    expect(data.institution).toContain("Centre for Climate Change and Sustainability Studies");
    expect(data.funding).toContain("DST-SERB");
    expect(data.scientific_simulation?.simulated_peak_discharge_m3s).toBeCloseTo(9.10, 1);
  });

  test("3. Verify PWA Web App Manifest", async ({ request }) => {
    const resp = await request.get("http://localhost:3000/manifest.json");
    expect(resp.status()).toBe(200);
    const manifest = await resp.json();

    expect(manifest.short_name).toBe("HydroCast");
    expect(manifest.background_color).toBe("#ffffff");
    expect(manifest.start_url).toBe("/dashboard");
    expect(manifest.disclaimer).toContain("Academic & Scientific Research Simulation");
  });
});

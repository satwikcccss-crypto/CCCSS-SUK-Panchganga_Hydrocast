"use client";
import React from "react";
import useSWR from "swr";
import { fetchDashboardData } from "@/lib/api";
import CrossSectionViewer from "@/components/CrossSectionViewer";

/** River cross-section viewer, same component as the public HydroCast site. */
export default function CrossSectionApp() {
  const { data, error } = useSWR("admin-dashboard-telemetry", () => fetchDashboardData(), { refreshInterval: 15000 });
  return (
    <div style={{ padding: 12 }}>
      {error && <p style={{ color: "var(--w-bad)", marginBottom: 8 }}>Dashboard data unavailable: {String(error.message)}. The surveyed section still draws; forecast levels need pipeline data.</p>}
      <div style={{ background: "#fff", border: "1px solid var(--w-line)", padding: 12 }}>
        <CrossSectionViewer bridgeShivaji={data?.bridgeShivaji} bridgeRajaram={data?.bridgeRajaram} defaultSite="SHIVAJI_BRIDGE" />
      </div>
    </div>
  );
}

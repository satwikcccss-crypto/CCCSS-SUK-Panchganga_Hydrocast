"use client";
import React from "react";
import AccuracyPanel from "@/components/AccuracyPanel";

/** Forecast run log + accuracy metrics. Reuses the public-site AccuracyPanel unchanged
 *  (KPI strip: Spearman, NSE, R², RMSE, PBIAS, lifecycle; tabs: charts, hourly log,
 *  WRD records, run ledger, adaptive ML). Opens on the run ledger. */
export default function ForecastRunsApp() {
  return (
    <div style={{ padding: 12 }}>
      <AccuracyPanel initialTab="runs" />
    </div>
  );
}

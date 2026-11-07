"use client";
import React from "react";

export function Group({ title, right, children, noPad }: { title: React.ReactNode; right?: React.ReactNode; children: React.ReactNode; noPad?: boolean }) {
  return (
    <section className="wa-group">
      <div className="hd"><span>{title}</span>{right}</div>
      <div className={noPad ? "" : "bd"}>{children}</div>
    </section>
  );
}

export function Tag({ kind, children }: { kind: "ok" | "warn" | "bad" | "idle"; children: React.ReactNode }) {
  return <span className={`wa-tag ${kind}`}>{children}</span>;
}

export function Meter({ pct, warnAt = 75, badAt = 90 }: { pct: number | null; warnAt?: number; badAt?: number }) {
  const v = pct == null ? 0 : Math.max(0, Math.min(100, pct));
  const cls = pct == null ? "" : v >= badAt ? "bad" : v >= warnAt ? "warn" : "";
  return <div className={`wa-bar ${cls}`}><i style={{ width: `${v}%` }} /></div>;
}

export const dash = "—";

export function fmtBytes(n: number | null | undefined): string {
  if (n == null || !isFinite(n)) return dash;
  const u = ["B", "KB", "MB", "GB", "TB"];
  let i = 0, v = n;
  while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
  return `${v.toFixed(i > 1 ? 1 : 0)} ${u[i]}`;
}

export function fmtDuration(s: number | null | undefined): string {
  if (s == null || !isFinite(s)) return dash;
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  return d ? `${d}d ${h}h ${m}m` : h ? `${h}h ${m}m` : `${m}m ${Math.floor(s % 60)}s`;
}

export function fmtTimeIST(iso: string | null | undefined): string {
  if (!iso) return dash;
  const d = new Date(iso);
  if (isNaN(d.getTime())) return dash;
  return d.toLocaleString("en-IN", { timeZone: "Asia/Kolkata", day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }) + " IST";
}

export function Spark({ values, max = 100, height = 46 }: { values: number[]; max?: number; height?: number }) {
  const W = 240;
  if (values.length < 2) return <div className="wa-note" style={{ height }}>Collecting samples…</div>;
  const step = W / Math.max(values.length - 1, 1);
  const pts = values.map((v, i) => `${(i * step).toFixed(1)},${(height - (Math.min(v, max) / max) * (height - 2) - 1).toFixed(1)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${height}`} width="100%" height={height} preserveAspectRatio="none" style={{ background: "#f4f9fe", border: "1px solid #bcd7ee" }} aria-label="History">
      <polyline points={pts} fill="none" stroke="#0078d4" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

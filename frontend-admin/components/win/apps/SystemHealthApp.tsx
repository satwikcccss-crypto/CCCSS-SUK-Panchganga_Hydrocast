"use client";
import React, { useEffect, useRef, useState } from "react";
import useSWR from "swr";
import { fetchDashboardData } from "@/lib/api";
import { Group, Tag, Meter, Spark, dash, fmtBytes, fmtDuration, fmtTimeIST } from "../ui";

export const fetchSystem = async () => {
  const r = await fetch("/api/admin/system", { cache: "no-store" });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
};

export default function SystemHealthApp() {
  const { data: sys, error } = useSWR("admin-system", fetchSystem, { refreshInterval: 5000 });
  const { data: dash0 } = useSWR("admin-dashboard-telemetry", () => fetchDashboardData(), { refreshInterval: 15000 });
  const [cpuHist, setCpuHist] = useState<number[]>([]);
  const last = useRef<string | null>(null);

  useEffect(() => {
    if (sys?.sampled_at && sys.sampled_at !== last.current && sys.host?.cpu_percent != null) {
      last.current = sys.sampled_at;
      setCpuHist((h) => [...h, sys.host.cpu_percent].slice(-60));
    }
  }, [sys]);

  if (error) return <div className="wa-pad"><Group title="System health"><p style={{ color: "var(--w-bad)" }}>/api/admin/system failed: {String(error.message)}</p></Group></div>;
  if (!sys) return <div className="wa-pad"><p className="wa-note">Reading host state…</p></div>;

  const h = sys.host;
  const memUsed = h.mem_total - h.mem_free;
  const memPct = (memUsed / h.mem_total) * 100;
  const diskUsed = h.disk ? h.disk.total - h.disk.free : null;
  const diskPct = h.disk ? (diskUsed! / h.disk.total) * 100 : null;
  const pl = dash0?.pipeline?.components ?? {};
  const issues: string[] = [];
  if (!sys.database.ok) issues.push("PostgreSQL port not reachable");
  if (!sys.backend.ok) issues.push("Backend API not reachable");
  const bad = (sys.services as any[]).filter((s) => !["RUNNING", "UNAVAILABLE"].includes(s.state));
  if (bad.length) issues.push(`${bad.length} service(s) not running`);

  return (
    <div className="wa-pad">
      <Group title="Overall" right={<Tag kind={issues.length ? "bad" : "ok"}>{issues.length ? "Attention needed" : "All monitored checks passing"}</Tag>}>
        {issues.length ? <ul style={{ margin: 0, paddingLeft: 18 }}>{issues.map((i) => <li key={i}>{i}</li>)}</ul>
          : <span className="wa-note">Checks: DB TCP port, backend HTTP response, Windows service state. Sampled {fmtTimeIST(sys.sampled_at)}.</span>}
      </Group>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(320px,1fr))", gap: 12 }}>
        <Group title="CPU" right={<span className="win-mono">{h.cpu_percent != null ? `${h.cpu_percent}%` : dash}</span>}>
          <Spark values={cpuHist} />
          <dl className="wa-kv" style={{ marginTop: 8 }}>
            <dt>Processor</dt><dd style={{ fontFamily: "inherit" }}>{h.cpu_model ?? dash}</dd>
            <dt>Logical processors</dt><dd>{h.cpu_count}</dd>
            <dt>Host uptime</dt><dd>{fmtDuration(h.uptime_s)}</dd>
          </dl>
        </Group>

        <Group title="Memory and disk">
          <div style={{ display: "grid", gap: 10 }}>
            <div>
              <div style={{ display: "flex", justifyContent: "space-between" }}><span>Memory</span><span className="win-mono">{fmtBytes(memUsed)} / {fmtBytes(h.mem_total)}</span></div>
              <Meter pct={memPct} />
            </div>
            <div>
              <div style={{ display: "flex", justifyContent: "space-between" }}><span>Disk {h.disk?.path ?? ""}</span><span className="win-mono">{h.disk ? `${fmtBytes(diskUsed)} / ${fmtBytes(h.disk.total)}` : dash}</span></div>
              <Meter pct={diskPct} warnAt={80} badAt={92} />
            </div>
            <dl className="wa-kv">
              <dt>Host</dt><dd>{h.name} ({h.platform} {h.release})</dd>
              <dt>Console process</dt><dd>PID {sys.console_process.pid} · {fmtBytes(sys.console_process.rss)} · Node {sys.console_process.node}</dd>
            </dl>
          </div>
        </Group>
      </div>

      <Group title="Database" right={<Tag kind={sys.database.ok ? "ok" : "bad"}>{sys.database.ok ? "Port open" : "Unreachable"}</Tag>}>
        <dl className="wa-kv">
          <dt>PostgreSQL endpoint</dt><dd>{sys.database.host}:{sys.database.port}</dd>
          <dt>TCP connect time</dt><dd>{sys.database.ms != null ? `${sys.database.ms} ms` : sys.database.error ?? dash}</dd>
          <dt>Pipeline-reported state store</dt><dd>{pl.database ?? dash}</dd>
          <dt>Run ledger rows exposed</dt><dd>{Array.isArray(dash0?.runs_history) ? dash0.runs_history.length : dash}</dd>
        </dl>
        <p className="wa-note" style={{ marginTop: 8 }}>The port check confirms something is listening; it does not test credentials, queries or replication. Set HYDROCAST_DB_HOST / HYDROCAST_DB_PORT if the database is elsewhere.</p>
      </Group>

      <Group title="Backend API" right={<Tag kind={sys.backend.ok ? "ok" : "bad"}>{sys.backend.ok ? `HTTP ${sys.backend.status}` : "Unreachable"}</Tag>}>
        <dl className="wa-kv">
          <dt>Base URL</dt><dd>{sys.backend.url}</dd>
          <dt>Response time</dt><dd>{sys.backend.ms != null ? `${sys.backend.ms} ms` : sys.backend.error ?? dash}</dd>
        </dl>
        <p className="wa-note" style={{ marginTop: 8 }}>Any HTTP reply (including 404 on “/”) counts as the server answering.</p>
      </Group>
    </div>
  );
}

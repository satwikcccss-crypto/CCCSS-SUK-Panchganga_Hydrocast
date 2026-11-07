"use client";
import React from "react";
import useSWR from "swr";
import { Group, Tag, dash, fmtTimeIST } from "../ui";
import { fetchSystem } from "./SystemHealthApp";

// Purpose text as written in the previous console. Service names come from HYDROCAST_SERVICES.
const PURPOSE: Record<string, string> = {
  HydrocastScheduler: "Pipeline cron daemon (00z, 06z, 12z, 18z)",
  HydrocastWorker: "Forecast engine and HEC-HMS executor",
  HydrocastWatchdog: "Heartbeat, stuck-pipeline abort, auto-restart",
  HydrocastBackend: "FastAPI REST and WebSocket server",
  HydrocastConsole: "This operator console",
};

const kind = (s: string) => (s === "RUNNING" ? "ok" : s === "UNAVAILABLE" || s === "UNKNOWN" ? "idle" : s.endsWith("_PENDING") ? "warn" : "bad") as "ok" | "bad" | "warn" | "idle";

export default function ServicesApp() {
  const { data, error } = useSWR("admin-system", fetchSystem, { refreshInterval: 5000 });
  const svcs: any[] = data?.services ?? [];
  const running = svcs.filter((s) => s.state === "RUNNING").length;
  const unavailable = svcs.length > 0 && svcs.every((s) => s.state === "UNAVAILABLE");

  return (
    <div className="wa-pad">
      <Group
        title="Background services (Windows Service Control Manager)"
        right={svcs.length ? <Tag kind={unavailable ? "idle" : running === svcs.length ? "ok" : "bad"}>{unavailable ? "Not a Windows host" : `${running} / ${svcs.length} running`}</Tag> : null}
        noPad
      >
        {error && <p style={{ padding: 10, color: "var(--w-bad)" }}>/api/admin/system failed: {String(error.message)}</p>}
        <table className="wa-table">
          <thead><tr><th>Name</th><th>Purpose</th><th style={{ width: 150 }}>State</th><th style={{ width: 70, textAlign: "right" }}>PID</th></tr></thead>
          <tbody>
            {!data && !error && <tr><td colSpan={4} className="wa-note">Querying services…</td></tr>}
            {svcs.map((s) => (
              <tr key={s.name}>
                <td className="win-mono" style={{ fontWeight: 600 }}>{s.name}</td>
                <td>{PURPOSE[s.name] ?? dash}</td>
                <td><Tag kind={kind(s.state)}>{s.state}</Tag>{s.note && <div className="wa-note">{s.note}</div>}</td>
                <td className="win-mono" style={{ textAlign: "right" }}>{s.pid ?? dash}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Group>
      <p className="wa-note">
        Read-only: state and PID come from <span className="win-mono">sc queryex</span>, sampled {fmtTimeIST(data?.sampled_at)}. A service reported NOT_INSTALLED means that name is
        not registered on this machine; edit the HYDROCAST_SERVICES environment variable if your NSSM service names differ.
      </p>
    </div>
  );
}

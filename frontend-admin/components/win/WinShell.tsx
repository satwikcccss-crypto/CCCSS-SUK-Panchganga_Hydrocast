"use client";
import React, { useCallback, useEffect, useRef, useState } from "react";
import useSWR from "swr";
import { ExternalLink } from "lucide-react";
import { fetchDashboardData } from "@/lib/api";
import { APPS } from "./apps";
import Window, { TASKBAR_H, WinState } from "./Window";

const PORTAL_URL = process.env.NEXT_PUBLIC_PUBLIC_PORTAL_URL || "https://cccss-suk-panchganga-hydrocast.vercel.app/dashboard";

function Clock() {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => { setNow(new Date()); const t = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(t); }, []);
  if (!now) return null;
  const o = { timeZone: "Asia/Kolkata" } as const;
  return (
    <div style={{ textAlign: "right", lineHeight: 1.25 }} title="Indian Standard Time">
      <div>{now.toLocaleTimeString("en-IN", { ...o, hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false })} IST</div>
      <div>{now.toLocaleDateString("en-IN", { ...o, day: "2-digit", month: "short", year: "numeric" })}</div>
    </div>
  );
}

const ALERT_COLOR: Record<string, string> = { NORMAL: "#6ccb5f", ALERT: "#ffd166", WARNING: "#ff9f6b", DANGER: "#ff6b6b", EMERGENCY: "#ff4d4d" };

export default function WinShell() {
  const [vp, setVp] = useState({ w: 0, h: 0 });
  const [wins, setWins] = useState<WinState[]>([]);
  const [startOpen, setStartOpen] = useState(false);
  const [sel, setSel] = useState<string | null>(null);
  const z = useRef(10);
  const booted = useRef(false);

  const { data, error } = useSWR("admin-dashboard-telemetry", () => fetchDashboardData(), { refreshInterval: 15000 });

  useEffect(() => {
    const f = () => setVp({ w: window.innerWidth, h: window.innerHeight });
    f(); window.addEventListener("resize", f);
    return () => window.removeEventListener("resize", f);
  }, []);

  const front = wins.filter((w) => !w.minimized).sort((a, b) => b.z - a.z)[0]?.id ?? null;

  const openApp = useCallback((id: string) => {
    const app = APPS.find((a) => a.id === id);
    if (!app || !vp.w) return;
    setStartOpen(false);
    setWins((ws) => {
      const next = ++z.current;
      if (ws.some((w) => w.id === id)) return ws.map((w) => (w.id === id ? { ...w, minimized: false, z: next } : w));
      const dh = vp.h - TASKBAR_H;
      const w = Math.round(Math.min(app.size.maxW, vp.w * app.size.w));
      const h = Math.round(Math.min(app.size.maxH, dh * app.size.h));
      const off = (ws.length % 6) * 28;
      return [...ws, { id, w, h, x: Math.max(0, Math.min(96 + off, vp.w - w)), y: Math.max(0, Math.min(8 + off, dh - h)), z: next, minimized: false, maximized: false }];
    });
  }, [vp]);

  // First dashboard section on load: forecast runs + accuracy.
  useEffect(() => { if (vp.w && !booted.current) { booted.current = true; openApp("runs"); } }, [vp, openApp]);

  const patch = (id: string, p: Partial<WinState>) => setWins((ws) => ws.map((w) => (w.id === id ? { ...w, ...p } : w)));
  const focus = (id: string) => setWins((ws) => (ws.find((w) => w.id === id)?.z === z.current ? ws : ws.map((w) => (w.id === id ? { ...w, z: ++z.current } : w))));
  const close = (id: string) => setWins((ws) => ws.filter((w) => w.id !== id));
  const taskClick = (id: string) => {
    const w = wins.find((x) => x.id === id);
    if (!w) return;
    if (!w.minimized && front === id) patch(id, { minimized: true });
    else setWins((ws) => ws.map((x) => (x.id === id ? { ...x, minimized: false, z: ++z.current } : x)));
  };

  useEffect(() => {
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setStartOpen(false); };
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, []);

  const alert: string | undefined = data?.status?.last_cycle?.alert_level;
  const cycle: string | undefined = data?.pipeline?.cycle ?? data?.cycle_id;

  return (
    <div className="win-root" onPointerDown={(e) => { if (!(e.target as HTMLElement).closest(".win-icon")) setSel(null); }}>
      <div className="win-icons" role="list">
        {APPS.map((a) => (
          <button key={a.id} role="listitem" className={`win-icon${sel === a.id ? " is-sel" : ""}`}
            onClick={() => setSel(a.id)} onDoubleClick={() => openApp(a.id)}
            onKeyDown={(e) => { if (e.key === "Enter") openApp(a.id); }}>
            <a.Icon size={34} color={a.color} strokeWidth={1.6} />
            <span className="lbl">{a.label}</span>
          </button>
        ))}
      </div>

      {vp.w > 0 && wins.map((w) => {
        const app = APPS.find((a) => a.id === w.id)!;
        return (
          <Window key={w.id} win={w} app={app} active={front === w.id} vw={vp.w} vh={vp.h}
            onFocus={() => focus(w.id)} onChange={(p) => patch(w.id, p)} onMinimize={() => patch(w.id, { minimized: true })} onClose={() => close(w.id)} />
        );
      })}

      {startOpen && (
        <>
          <div style={{ position: "absolute", inset: 0, zIndex: 100000 }} onPointerDown={() => setStartOpen(false)} />
          <nav className="win-startmenu" aria-label="Start menu">
            <header>
              <div style={{ fontWeight: 600, fontSize: 14 }}>HydroCast Operator Console</div>
              <div style={{ opacity: 0.7, marginTop: 2 }}>CCCSS, Shivaji University, Kolhapur</div>
            </header>
            {APPS.map((a) => <button key={a.id} onClick={() => openApp(a.id)}><a.Icon size={18} color={a.color} />{a.label}</button>)}
            <footer><a href={PORTAL_URL} target="_blank" rel="noreferrer"><ExternalLink size={16} />Open public portal</a></footer>
          </nav>
        </>
      )}

      <div className="win-taskbar">
        <button className={`win-start${startOpen ? " is-open" : ""}`} aria-label="Start" aria-expanded={startOpen} onClick={() => setStartOpen((s) => !s)}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="#4cc2ff"><rect x="0" y="0" width="8.4" height="8.4" /><rect x="9.6" y="0" width="8.4" height="8.4" /><rect x="0" y="9.6" width="8.4" height="8.4" /><rect x="9.6" y="9.6" width="8.4" height="8.4" /></svg>
        </button>
        {wins.map((w) => {
          const app = APPS.find((a) => a.id === w.id)!;
          return (
            <button key={w.id} className={`win-task ${front === w.id ? "is-front" : "is-open"}`} onClick={() => taskClick(w.id)} title={app.title}>
              <app.Icon size={16} color={app.color} /><span>{app.label}</span>
            </button>
          );
        })}
        <div className="win-tray">
          <span title={error ? "Pipeline state unreadable" : cycle ? `Latest cycle ${cycle}` : "No cycle published"} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <i style={{ width: 9, height: 9, borderRadius: 5, background: error ? "#ff6b6b" : alert ? ALERT_COLOR[alert] ?? "#bbb" : "#888", display: "inline-block" }} />
            {error ? "State unreadable" : alert ? `Flood status: ${alert}` : "No data"}
          </span>
          {cycle && <span className="win-mono" style={{ opacity: 0.85 }}>{cycle}</span>}
          <Clock />
        </div>
      </div>
    </div>
  );
}

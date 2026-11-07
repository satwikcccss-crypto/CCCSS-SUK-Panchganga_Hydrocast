"use client";
import React from "react";
import type { AppDef } from "./apps";

export type WinState = {
  id: string; x: number; y: number; w: number; h: number; z: number;
  minimized: boolean; maximized: boolean;
};

export const TASKBAR_H = 40;
const MIN_W = 420, MIN_H = 260;
const clamp = (v: number, lo: number, hi: number) => Math.min(Math.max(v, lo), hi);

type Props = {
  win: WinState; app: AppDef; active: boolean; vw: number; vh: number;
  onFocus: () => void; onChange: (patch: Partial<WinState>) => void; onMinimize: () => void; onClose: () => void;
};

const Glyph = {
  min: <svg width="10" height="10" viewBox="0 0 10 10"><path d="M0 5.5h10" stroke="currentColor" /></svg>,
  max: <svg width="10" height="10" viewBox="0 0 10 10"><rect x="0.5" y="0.5" width="9" height="9" fill="none" stroke="currentColor" /></svg>,
  restore: <svg width="10" height="10" viewBox="0 0 10 10"><rect x="0.5" y="2.5" width="7" height="7" fill="none" stroke="currentColor" /><path d="M2.5 2.5v-2h7v7h-2" fill="none" stroke="currentColor" /></svg>,
  close: <svg width="10" height="10" viewBox="0 0 10 10"><path d="M0 0l10 10M10 0L0 10" stroke="currentColor" /></svg>,
};

export default function Window({ win, app, active, vw, vh, onFocus, onChange, onMinimize, onClose }: Props) {
  const deskH = vh - TASKBAR_H;
  const geo = win.maximized ? { left: 0, top: 0, width: vw, height: deskH } : { left: win.x, top: win.y, width: win.w, height: win.h };

  const drag = (e: React.PointerEvent) => {
    if (win.maximized || e.button !== 0) return;
    if ((e.target as HTMLElement).closest(".win-ctl")) return;
    e.preventDefault();
    const sx = e.clientX, sy = e.clientY, ox = win.x, oy = win.y;
    const move = (ev: PointerEvent) => onChange({ x: clamp(ox + ev.clientX - sx, 120 - win.w, vw - 120), y: clamp(oy + ev.clientY - sy, 0, deskH - 31) });
    const up = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up); };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  };

  const resize = (dir: string) => (e: React.PointerEvent) => {
    if (win.maximized || e.button !== 0) return;
    e.preventDefault(); e.stopPropagation(); onFocus();
    const sx = e.clientX, sy = e.clientY, { x, y, w, h } = win;
    const move = (ev: PointerEvent) => {
      const dx = ev.clientX - sx, dy = ev.clientY - sy;
      let nx = x, ny = y, nw = w, nh = h;
      if (dir.includes("e")) nw = Math.max(MIN_W, w + dx);
      if (dir.includes("s")) nh = Math.max(MIN_H, h + dy);
      if (dir.includes("w")) { nw = Math.max(MIN_W, w - dx); nx = x + (w - nw); }
      if (dir.includes("n")) { nh = Math.max(MIN_H, h - dy); ny = Math.max(0, y + (h - nh)); nh = h - (ny - y); }
      onChange({ x: nx, y: ny, w: nw, h: nh });
    };
    const up = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up); };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  };

  const grips: [string, React.CSSProperties, string][] = [
    ["n", { top: -3, left: 6, right: 6, height: 6 }, "ns-resize"], ["s", { bottom: -3, left: 6, right: 6, height: 6 }, "ns-resize"],
    ["w", { left: -3, top: 6, bottom: 6, width: 6 }, "ew-resize"], ["e", { right: -3, top: 6, bottom: 6, width: 6 }, "ew-resize"],
    ["nw", { top: -3, left: -3, width: 10, height: 10 }, "nwse-resize"], ["ne", { top: -3, right: -3, width: 10, height: 10 }, "nesw-resize"],
    ["sw", { bottom: -3, left: -3, width: 10, height: 10 }, "nesw-resize"], ["se", { bottom: -3, right: -3, width: 10, height: 10 }, "nwse-resize"],
  ];

  return (
    <div
      className={`win-window${active ? " is-active" : ""}${win.maximized ? " is-max" : ""}`}
      style={{ ...geo, zIndex: win.z, display: win.minimized ? "none" : "flex" }}
      onPointerDownCapture={onFocus}
      role="dialog"
      aria-label={app.title}
    >
      <div className="win-title" onPointerDown={drag} onDoubleClick={() => onChange({ maximized: !win.maximized })}>
        <div className="ttl"><app.Icon size={14} color="#0078d4" strokeWidth={2.2} /><span>{app.title}</span></div>
        <button className="win-ctl" aria-label="Minimize" onClick={onMinimize}>{Glyph.min}</button>
        <button className="win-ctl" aria-label={win.maximized ? "Restore" : "Maximize"} onClick={() => onChange({ maximized: !win.maximized })}>{win.maximized ? Glyph.restore : Glyph.max}</button>
        <button className="win-ctl close" aria-label="Close" onClick={onClose}>{Glyph.close}</button>
      </div>
      <div className="win-body"><app.Component /></div>
      {!win.maximized && grips.map(([d, st, cur]) => <div key={d} className="win-grip" style={{ ...st, cursor: cur }} onPointerDown={resize(d)} />)}
    </div>
  );
}

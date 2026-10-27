"""
Build comprehensive Excel workbook for August 2025 Shivaji Bridge flood analysis.

Contents (all inputs + outputs):
  1. Inputs_Configuration  - event config, thresholds, stage/rainfall inputs
  2. Hourly_Rainfall_Subbasin - hourly rainfall per subbasin (input)
  3. Subbasin_Runoff_Stats - per-subbasin runoff statistics (output)
  4. Accuracy_Metrics - all iterations / strategies / best life-safety runs (output)
  5. Hydrograph_Hourly_Inputs_Outputs - hourly observed vs sim stage/discharge (I/O)
  6. Plots_And_Notes - embedded hydrograph plot images + notes

Saves to: historical_checks/2025_august_shivaji_bridge/results/dynamic_calibration/August_2025_Shivaji_Bridge_Analysis.xlsx
"""
import json
import copy
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.drawing.image import Image as XLImage

REPO = Path("E:/hydrocast_complete")
BRIDGE = REPO / "historical_checks" / "2025_august_shivaji_bridge"
import sys as _sys
_sys.path.insert(0, str(REPO))
_sys.path.insert(0, str(REPO / "historical_checks"))

from src.hms.basin_parser import load_immutable_baseline
from src.hms.runner import _execute_hec_hms_core
from src.hydrology.stage_converter import convert_discharge_to_stage_manning, convert_stage_to_discharge_manning
from src.hydrology.validation_metrics import compute_nse, compute_rmse_mae, compute_kge, compute_pbias
from src.ecmwf.station_selector import STATION_REGISTRY, select_active_subbasin_gages
from run_historical_event import fetch_historical_rainfall_for_station   # noqa: E402

START = "2025-08-08"
END = "2025-08-22"
HOURS = 360
RUN_DT = datetime(2025, 8, 8, 0, 0, 0)
OUT_DIR = BRIDGE / "results" / "dynamic_calibration"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SUBS = [f"S{i}" for i in range(1, 10)]
CN_USED = 90.0          # absolute CN used in best life-safety run
IA_FRAC = 0.05          # saturated monsoon initial abstraction
S_BASE = (25400.0 / CN_USED) - 254.0   # SCS storage = 28.22 mm
IA = IA_FRAC * S_BASE

OUTPUT_XLSX = OUT_DIR / "August_2025_Shivaji_Bridge_Analysis.xlsx"


def fetch_hyetographs():
    station_ts, station_cum = {}, {}
    for st in STATION_REGISTRY:
        series = fetch_historical_rainfall_for_station(st.lat, st.lon, START, END, hours=HOURS)
        station_ts[st.station_id] = series
        station_cum[st.station_id] = float(np.sum(series))
    sel = select_active_subbasin_gages(station_cum)
    hyetos = {}
    for sub in SUBS:
        info = sel.get(sub, {})
        sid = info.get("selected_station_id", "KARVEER")
        hyetos[sub] = station_ts.get(sid, np.zeros(HOURS, dtype=np.float32)).copy()
    return hyetos, sel


def compute_excess(rain_mm):
    """SCS excess precipitation with Ia = 0.05*S, CN = 90 (per hour, cumulative)."""
    cum = np.cumsum(rain_mm)
    cum_prev = np.concatenate(([0.0], cum[:-1]))
    exc = np.maximum(0.0, cum - IA) - np.maximum(0.0, cum_prev - IA)
    return np.maximum(0.0, exc)


def main():
    hyetos, sel = fetch_hyetographs()
    obs = pd.read_csv(REPO / "data" / "shivaji_bridge_2025_hourly_observed.csv",
                      parse_dates=["timestamp"]).dropna(subset=["stage_m"])

    # ---------- Sheet 2: Hourly rainfall ----------
    rain_rows = []
    for sub in SUBS:
        info = sel.get(sub, {})
        sid = info.get("selected_station_id", "KARVEER")
        st_name = info.get("station_name", sid)
        rain = np.asarray(hyetos[sub], dtype=np.float64)
        cum = np.cumsum(rain)
        exc = compute_excess(rain)
        for h in range(HOURS):
            ts = pd.Timestamp("2025-08-08 00:00:00") + pd.Timedelta(hours=h)
            rain_rows.append({
                "subbasin": sub, "hour_index": h, "timestamp": ts,
                "governing_station_id": sid, "station_name": st_name,
                "rainfall_mm": round(float(rain[h]), 3),
                "cumulative_mm": round(float(cum[h]), 3),
                "excess_mm": round(float(exc[h]), 3),
            })
    rain_df = pd.DataFrame(rain_rows)

    # ---------- Sheet 3: Subbasin runoff stats ----------
    sub_stats = []
    for sub in SUBS:
        info = sel.get(sub, {})
        sid = info.get("selected_station_id", "KARVEER")
        st_name = info.get("station_name", sid)
        rain = np.asarray(hyetos[sub], dtype=np.float64)
        cum = np.cumsum(rain)
        exc = compute_excess(rain)
        sub_stats.append({
            "subbasin": sub, "area_km2": float(info.get("area_km2", 0.0)),
            "governing_station_id": sid, "station_name": st_name,
            "total_rain_mm": round(float(cum[-1]), 3),
            "cn_used": CN_USED, "ia_used": round(float(IA), 4),
            "total_excess_mm": round(float(exc.sum()), 3),
            "peak_excess_mm": round(float(exc.max()), 3),
            "peak_excess_hour": int(exc.argmax()),
        })
    sub_stats_df = pd.DataFrame(sub_stats)

    # ---------- Sheet 4: Accuracy metrics ----------
    acc_rows = []
    def add_acc(label, r):
        if r is None:
            return
        acc_rows.append({
            "iteration": label, "nse": r.get("nse"), "kge": r.get("kge"),
            "rmse_m": r.get("rmse"), "mae_m": r.get("mae"), "pbias_pct": r.get("pbias"),
            "peak_err_m": r.get("peak_err_m"), "peak_timing_err_h": r.get("peak_timing_err_h"),
            "obs_peak_m": r.get("obs_peak_m"), "sim_peak_m": r.get("sim_peak_m"),
            "obs_peak_ts": r.get("obs_peak_ts"), "sim_peak_ts": r.get("sim_peak_ts"),
            "peak_q_err_m3s": r.get("peak_q_err_m3s"), "matched_hours": r.get("matched"),
        })
    dcr = json.load(open(OUT_DIR / "dynamic_calibration_results.json", "r", encoding="utf-8"))
    for it in dcr.get("iterations", []):
        add_acc(it.get("label", "?"), it)
    # best life-safety run
    fin = json.load(open(OUT_DIR / "final_uhmexp_results.json", "r", encoding="utf-8"))
    for r in fin.get("all_results", []):
        p = r.get("params", {})
        acc_rows.append({
            "iteration": f"best_final_uhmexp_mexp={p.get('uh_m_exp')}",
            "nse": r.get("nse"), "kge": r.get("kge"), "rmse_m": r.get("rmse"),
            "mae_m": r.get("mae"), "pbias_pct": r.get("pbias"),
            "peak_err_m": r.get("peak_err_m"), "peak_timing_err_h": r.get("peak_timing_err_h"),
            "obs_peak_m": r.get("obs_peak_m"), "sim_peak_m": r.get("sim_peak_m"),
            "obs_peak_ts": r.get("sim_peak_ts"), "sim_peak_ts": r.get("sim_peak_ts"),
            "peak_q_err_m3s": None, "matched_hours": r.get("matched"),
            "_params": p,
        })
    # window strategies
    ws = json.load(open(BRIDGE / "results" / "90h_windows" / "window_strategy_comparison.json", "r", encoding="utf-8"))
    def find_key(obj, keys):
        cur = obj
        for k in keys:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                return None
        return cur
    wsm = find_key(ws, ["strategies", "comparison", "strategies"]) if ws else None
    strategies = wsm if isinstance(wsm, list) else (wsm or [])
    for s in strategies:
        acc_rows.append({
            "iteration": f"window_{s.get('strategy_id', s.get('name', '?'))}",
            "nse": s.get("nse"), "kge": s.get("kge"), "rmse_m": s.get("rmse"),
            "mae_m": s.get("mae"), "pbias_pct": s.get("pbias"),
            "peak_err_m": s.get("peak_err_m") or s.get("peak_error_m"),
            "peak_timing_err_h": s.get("peak_timing_err_h") or s.get("timing_error_h"),
            "obs_peak_m": None, "sim_peak_m": None, "obs_peak_ts": None, "sim_peak_ts": None,
            "peak_q_err_m3s": None, "matched_hours": None,
        })
    acc_df = pd.DataFrame(acc_rows)

    # ---------- Sheet 5: Hydrograph hourly I/O ----------
    aligned = pd.read_csv(OUT_DIR / "hydrograph_aligned.csv",
                          parse_dates=["timestamp"]).drop_duplicates(subset=["timestamp"])
    hydro_df = aligned.copy()

    # ---------- Build Excel ----------
    wb = Workbook()

    # Sheet 1
    ws1 = wb.active
    ws1.title = "Inputs_Configuration"
    cfg = [
        ("Event", "2025_august - August 2025 Flood - Shivaji Bridge"),
        ("start_date", "2025-08-08"), ("end_date", "2025-08-22"),
        ("sim_hours", 360), ("observed_csv", "data/shivaji_bridge_2025_hourly_observed.csv"),
        ("observed_peak_stage_m", 542.57), ("observed_peak_ts", "2025-08-21 14:00:00"),
        ("stage_formula", "stage_m = 549.35 - field1_ft * 0.3048"),
        ("bed_rl_m", 528.67), ("deck_m", 549.35),
        ("alert_stage_m", 542.10), ("warning_stage_m", 542.70), ("danger_stage_m", 543.30),
        ("hfl_m", 545.33),
        ("rainfall_source", "Open-Meteo Historical Archive /v1/archive hourly=precipitation"),
        ("mean_catchment_rain_mm", 465.5),
        ("amc_regime", "AMC-III (saturated soil)"),
        ("best_run_lag_min", 2700), ("best_run_k_hr", 6.0), ("best_run_cn", 90.0),
        ("best_run_muskingum_x", 0.15), ("best_run_ia_frac", 0.05),
        ("best_run_uh_max_hr", 90), ("best_run_uh_m_exp", 50),
    ]
    for r in cfg:
        ws1.append(list(r))

    # Sheet 2: Hourly rainfall
    ws2 = wb.create_sheet("Hourly_Rainfall_Subbasin")
    for c, col in enumerate(rain_df.columns, start=1):
        ws2.cell(row=1, column=c, value=str(col))
    for r, (_, row) in enumerate(rain_df.iterrows(), start=2):
        ws2.cell(row=r, column=1, value=str(row["subbasin"]))
        ws2.cell(row=r, column=2, value=int(row["hour_index"]))
        ws2.cell(row=r, column=3, value=row["timestamp"])
        ws2.cell(row=r, column=4, value=str(row["governing_station_id"]))
        ws2.cell(row=r, column=5, value=str(row["station_name"]))
        ws2.cell(row=r, column=6, value=float(row["rainfall_mm"]))
        ws2.cell(row=r, column=7, value=float(row["cumulative_mm"]))
        ws2.cell(row=r, column=8, value=float(row["excess_mm"]))

    # Sheet 3: Subbasin runoff stats
    ws3 = wb.create_sheet("Subbasin_Runoff_Stats")
    sub_stats_df_headers = list(sub_stats_df.columns)
    for c, col in enumerate(sub_stats_df_headers, start=1):
        ws3.cell(row=1, column=c, value=str(col))
    for r, (_, row) in enumerate(sub_stats_df.iterrows(), start=2):
        for c, col in enumerate(list(sub_stats_df.columns), start=1):
            ws3.cell(row=r, column=c, value=row[col])

    # Sheet 4: Accuracy metrics
    ws4 = wb.create_sheet("Accuracy_Metrics")
    acc_headers = list(acc_df.columns)
    for c, col in enumerate(acc_headers, start=1):
        ws4.cell(row=1, column=c, value=str(col))
    for r, (_, row) in enumerate(acc_df.iterrows(), start=2):
        for c, col in enumerate(acc_headers, start=1):
            v = row[col]
            if isinstance(v, dict):
                v = json.dumps(v)
            ws4.cell(row=r, column=c, value=v)

    # Sheet 5: Hydrograph I/O
    ws5 = wb.create_sheet("Hydrograph_Hourly_Inputs_Outputs")
    cols5 = list(hydro_df.columns)
    for c, col in enumerate(cols5, start=1):
        ws5.cell(row=1, column=c, value=str(col))
    for r, (_, row) in enumerate(hydro_df.iterrows(), start=2):
        ws5.cell(row=r, column=1, value=row["timestamp"])
        for c, col in enumerate(cols5[1:], start=2):
            v = row[col]
            ws5.cell(row=r, column=c, value=float(v) if isinstance(v, (int, float, np.floating)) else v)

    # Sheet 6: Plots + notes
    ws6 = wb.create_sheet("Plots_And_Notes")
    ws6.cell(row=1, column=1, value="August 2025 Shivaji Bridge - HydroCast Analysis")
    for note_row in [
        ("NOTE: This workbook consolidates hourly rainfall, subbasin runoff, accuracy and hydrograph I/O for the Aug 2025 flood event.", 3),
        ("NOTE: Best life-safety run params: lag=2700min k=6.0cn90 x=0.15 Ia=0.05 uhmax=90 uhmexp=50 -> NSE=0.859 KGE=0.815 peak_err=+0.11m timing=+3.0h.", 4),
        ("NOTE: Full session log: results/dynamic_calibration/CALIBRATION_SESSION_LOG_2026_10_22.md", 5),
    ]:
        ws6.cell(row=note_row[1], column=1, value=note_row[0])
    plot_files = [
        OUT_DIR / "hydrograph_static_vs_dynamic.png",
        OUT_DIR / "hydrograph_best_nse.png",
        OUT_DIR / "hydrograph_best_nse_peak_zoom.png",
        OUT_DIR / "hydrograph_static_vs_dynamic_peak_zoom.png",
    ]
    for i, img_path in enumerate(plot_files):
        if img_path.exists():
            xl_img = XLImage(str(img_path))
            xl_img.width = 640
            xl_img.height = 380
            ws6.add_image(xl_img, f"P{i+1}")

    wb.save(str(OUTPUT_XLSX))
    print(f"Saved Excel: {OUTPUT_XLSX}")


if __name__ == "__main__":
    main()

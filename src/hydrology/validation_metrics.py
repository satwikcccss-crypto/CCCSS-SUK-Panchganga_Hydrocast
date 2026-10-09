"""
Hydrological Forecast Validation & Accuracy Metrics Engine
===========================================================
Evaluates model accuracy against actual ground truth observed telemetry:
  - Spearman Rank Correlation (ρ)
  - Pearson Correlation (r & R²)
  - Nash-Sutcliffe Efficiency (NSE)
  - Root Mean Square Error (RMSE) & Mean Absolute Error (MAE)
  - Percent Bias / Volumetric Runoff Error (PBIAS %)
  - Station-Wise Rainfall Volume Accuracy (18 Panchganga Stations)
  - Lead-Time Accuracy Degradation Curve (T+0 to T+90)
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from scipy import stats

log = logging.getLogger(__name__)


def compute_spearman_correlation(predicted: np.ndarray, observed: np.ndarray) -> Tuple[float, float]:
    """Computes Spearman rank correlation coefficient and p-value."""
    if len(predicted) < 3 or len(observed) < 3:
        return 0.0, 1.0
    if np.std(predicted) < 1e-9 or np.std(observed) < 1e-9:
        return (1.0 if np.allclose(predicted, observed, atol=1e-3) else 0.0), 0.0
    res = stats.spearmanr(predicted, observed)
    rho = float(res.statistic) if hasattr(res, "statistic") else float(res[0])
    pval = float(res.pvalue) if hasattr(res, "pvalue") else float(res[1])
    return (0.0 if np.isnan(rho) else round(rho, 4)), (1.0 if np.isnan(pval) else round(pval, 6))


def compute_pearson_correlation(predicted: np.ndarray, observed: np.ndarray) -> Tuple[float, float, float]:
    """Computes Pearson correlation coefficient (r), R², and p-value."""
    if len(predicted) < 3 or len(observed) < 3:
        return 0.0, 0.0, 1.0
    if np.std(predicted) < 1e-9 or np.std(observed) < 1e-9:
        match = 1.0 if np.allclose(predicted, observed, atol=1e-3) else 0.0
        return match, match, 0.0
    res = stats.pearsonr(predicted, observed)
    r = float(res.statistic) if hasattr(res, "statistic") else float(res[0])
    pval = float(res.pvalue) if hasattr(res, "pvalue") else float(res[1])
    r_clean = 0.0 if np.isnan(r) else r
    r2 = r_clean ** 2
    return round(r_clean, 4), round(r2, 4), (1.0 if np.isnan(pval) else round(pval, 6))


def compute_nse(predicted: np.ndarray, observed: np.ndarray) -> float:
    """
    Computes Nash-Sutcliffe Model Efficiency (NSE):
    NSE = 1 - (sum((Q_obs - Q_sim)^2) / sum((Q_obs - mean(Q_obs))^2))
    """
    if len(predicted) < 3 or len(observed) < 3:
        return 0.0
    numerator = np.sum((observed - predicted) ** 2)
    denominator = np.sum((observed - np.mean(observed)) ** 2)
    if denominator < 1e-6:
        return 1.0 if numerator < 1e-6 else 0.0
    nse = 1.0 - (numerator / denominator)
    return round(float(nse), 4)


def compute_rmse_mae(predicted: np.ndarray, observed: np.ndarray) -> Tuple[float, float]:
    """Computes Root Mean Square Error (RMSE) and Mean Absolute Error (MAE)."""
    if len(predicted) == 0 or len(observed) == 0:
        return 0.0, 0.0
    rmse = np.sqrt(np.mean((predicted - observed) ** 2))
    mae = np.mean(np.abs(predicted - observed))
    return round(float(rmse), 3), round(float(mae), 3)


def compute_pbias(predicted: np.ndarray, observed: np.ndarray) -> float:
    """
    Computes Percent Bias (PBIAS %):
    PBIAS = (sum(predicted - observed) / sum(observed)) * 100
    """
    sum_obs = np.sum(observed)
    if abs(sum_obs) < 1e-6:
        return 0.0
    pbias = (np.sum(predicted - observed) / sum_obs) * 100.0
    return round(float(pbias), 2)


def evaluate_forecast_accuracy(run_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive forecast validation comparing predicted stage/flow against
    actual observed sensor data, plus 18-station rainfall volume verification.
    """
    actual_obs = run_state.get("actual_observed", [])
    shivaji_fc = run_state.get("bridgeShivaji", {}).get("forecast", [])

    # If actual observations are not explicitly present, query real ThingSpeak sensor feeds
    if not actual_obs and shivaji_fc:
        try:
            from src.hydrology.realtime_telemetry_validator import validate_active_cycle
            cycle_id = run_state.get("cycle_id") or run_state.get("summary", {}).get("cycle_id")
            val_res = validate_active_cycle(run_id=cycle_id)
            actual_obs = val_res.get("actual_observed_series", [])
        except Exception as e:
            log.warning("Real-time telemetry validation query failed: %s", e)
            actual_obs = []

    # Filter strictly to points with valid physical observations (no synthetic noise)
    valid_points = [pt for pt in actual_obs if pt.get("observed_stage_m") is not None]
    if not valid_points:
        return {
            "status": "AWAITING_TELEMETRY",
            "lifecycle_status": "IN_PROGRESS",
            "verified_hours": 0,
            "total_forecast_hours": len(shivaji_fc),
            "performance_grade": "ACCUMULATING_TELEMETRY",
            "badge_color": "sky",
            "metrics": {
                "sample_size_hours": 0,
                "spearman_rho": None,
                "spearman_rho_q": None,
                "nse_stage": None,
                "nse_discharge": None,
                "rmse_stage_m": None,
                "mae_stage_m": None,
                "pbias_stage_pct": None,
                "pearson_r2": None,
                "basin_rainfall_accuracy_pct": 100.0,
            },
            "station_volume_accuracy": [],
            "scatter_points": [],
            "lead_time_decay": [],
            "actual_observed_series": actual_obs,
        }

    pred_stages = np.array([pt["predicted_stage_m"] for pt in valid_points], dtype=np.float64)
    obs_stages = np.array([pt["observed_stage_m"] for pt in valid_points], dtype=np.float64)
    pred_q = np.array([pt["predicted_discharge_m3s"] for pt in valid_points], dtype=np.float64)
    # Never substitute the prediction for a missing observation. If the observed
    # discharge is absent the pair is dropped so the discharge metrics are not
    # computed against the forecast's own values (which would score a perfect
    # self-agreement).
    q_pairs = [
        (pt["predicted_discharge_m3s"], pt["observed_discharge_m3s"])
        for pt in valid_points
        if pt.get("observed_discharge_m3s") is not None
    ]
    if q_pairs:
        pred_q = np.array([p for p, _ in q_pairs], dtype=np.float64)
        obs_q = np.array([o for _, o in q_pairs], dtype=np.float64)
    else:
        pred_q = obs_q = None

    from src.hydrology.stage_converter import assess_low_flow_guard

    # Low-flow representativeness. During stable baseflow a constant offset is a
    # datum/anchor bias, and observed stages below the lowest WRD gauge make the
    # rating a shape extrapolation. Both are surfaced so a ~2 m baseflow bias is
    # never reported as an ordinary, well-behaved MAE.
    low_flow_guard = assess_low_flow_guard(pred_stages, obs_stages)

    # Flat-flow guard: during baseflow-only (no active storm), both predicted and observed
    # series are nearly constant. NSE and Spearman are undefined/meaningless in this case.
    obs_std = float(np.std(obs_stages))
    if obs_std < 0.05:  # less than 5cm variance -> baseflow stable
        rmse_stage, mae_stage = compute_rmse_mae(pred_stages, obs_stages)
        rmse_q, mae_q = compute_rmse_mae(pred_q, obs_q)
        baseflow_mismatch = bool(low_flow_guard["constant_bias_detected"])
        return {
            "status": "BASEFLOW_MISMATCH" if baseflow_mismatch else "BASEFLOW_STABLE",
            "lifecycle_status": "BASEFLOW_STABLE",
            "verified_hours": len(valid_points),
            "total_forecast_hours": len(shivaji_fc),
            "performance_grade": "BASEFLOW_MISMATCH" if baseflow_mismatch else "BASEFLOW_STABLE",
            "badge_color": "rose" if baseflow_mismatch else "sky",
            "low_flow_guard": low_flow_guard,
            "metrics": {
                "sample_size_hours": len(valid_points),
                "spearman_rho": None,
                "spearman_rho_q": None,
                "nse_stage": None,
                "nse_discharge": None,
                "rmse_stage_m": round(float(rmse_stage), 3),
                "mae_stage_m": round(float(mae_stage), 3),
                "pbias_stage_pct": None,
                "pearson_r2": None,
                "basin_rainfall_accuracy_pct": None,
                "baseflow_stage_offset_m": low_flow_guard["baseflow_stage_offset_m"],
                "observed_ungauged_fraction": low_flow_guard["ungauged_fraction"],
                "rating_extrapolated": low_flow_guard["rating_extrapolated"],
                "constant_baseflow_bias": baseflow_mismatch,
                "baseflow_note": low_flow_guard["note"],
            },
            "station_volume_accuracy": [],
            "scatter_points": [],
            "lead_time_decay": [],
            "actual_observed_series": actual_obs,
        }

    # Skill metrics (NSE, Spearman, Pearson) require a minimum matched sample size
    # and enough observed spread; otherwise the NSE denominator collapses and the
    # score is numerically unstable rather than informative.
    from src.hydrology.realtime_telemetry_validator import (
        MIN_CORRELATION_SAMPLES,
        MIN_OBS_Q_STD_M3S,
        MIN_OBS_STAGE_STD_M,
    )

    obs_std = float(np.std(obs_stages))
    nse_reliable = (
        len(valid_points) >= MIN_CORRELATION_SAMPLES
        and obs_std >= MIN_OBS_STAGE_STD_M
    )

    # 1. Spearman Correlation (Non-linear monotonic rank tracking)
    #    Gated on the same reliability conditions as NSE.
    if nse_reliable:
        spearman_rho_stage, pval_spearman_stage = compute_spearman_correlation(pred_stages, obs_stages)
    else:
        spearman_rho_stage, pval_spearman_stage = None, None
    spearman_rho_q = None
    pval_spearman_q = None

    # 2. Pearson Correlation & R²
    if nse_reliable:
        r_stage, r2_stage, pval_pearson = compute_pearson_correlation(pred_stages, obs_stages)
    else:
        r_stage, r2_stage, pval_pearson = None, None, None

    # 3. Nash-Sutcliffe Efficiency (NSE) and 4/5 error metrics.
    nse_stage = compute_nse(pred_stages, obs_stages) if nse_reliable else None

    # 4. RMSE & MAE (well defined for any sample size)
    rmse_stage, mae_stage = compute_rmse_mae(pred_stages, obs_stages)
    if pred_q is not None and len(pred_q) > 0:
        q_obs_std = float(np.std(obs_q))
        nse_q_reliable = (
            len(pred_q) >= MIN_CORRELATION_SAMPLES and q_obs_std >= MIN_OBS_Q_STD_M3S
        )
        nse_q = compute_nse(pred_q, obs_q) if nse_q_reliable else None
        rmse_q, mae_q = compute_rmse_mae(pred_q, obs_q)
        pbias_q = compute_pbias(pred_q, obs_q) if nse_q_reliable else None
        rho_q = compute_spearman_correlation(pred_q, obs_q)[0] if nse_q_reliable else None
    else:
        nse_q = rmse_q = mae_q = pbias_q = rho_q = None

    # 5. Percent Bias (PBIAS) for stage
    pbias_stage = compute_pbias(pred_stages, obs_stages)

    # Performance grade. Uses NSE and Spearman as conjunctive conditions, and
    # never awards a rating better than CALIBRATION REQUIRED when a reliably
    # computed NSE is zero or negative.
    if nse_q is not None and spearman_rho_q is not None:
        if nse_q >= 0.80 and spearman_rho_q >= 0.85:
            performance_grade = "EXCELLENT"
            badge_color = "emerald"
        elif nse_q >= 0.65 and spearman_rho_q >= 0.75:
            performance_grade = "VERY GOOD"
            badge_color = "sky"
        elif nse_q >= 0.50:
            performance_grade = "SATISFACTORY"
            badge_color = "amber"
        elif nse_q > 0.0:
            performance_grade = "MODERATE BIAS"
            badge_color = "amber"
        else:
            performance_grade = "CALIBRATION REQUIRED"
            badge_color = "rose"
    elif not nse_reliable:
        # Skill metrics undefined: too few matched hours, or stable baseflow.
        performance_grade = "ACCUMULATING TELEMETRY" if len(valid_points) < MIN_CORRELATION_SAMPLES else "BASEFLOW STABLE"
        badge_color = "sky"
    else:
        performance_grade = "CALIBRATION REQUIRED"
        badge_color = "rose"

    # 6. Station Rainfall Volume Accuracy (via Multi-tier Observed Rainfall Pipeline)
    stations_data = run_state.get("stations", [])
    try:
        from src.hydrology.observed_rainfall_pipeline import validate_station_rainfall
        streamflow_obs = [
            p["observed_discharge_m3s"]
            for p in actual_obs
            if p.get("observed_discharge_m3s") is not None
        ]
        station_volume_accuracy, rain_summary = validate_station_rainfall(stations_data, streamflow_obs)
        basin_rain_error_pct = rain_summary["basin_error_pct"]
        basin_rain_accuracy_pct = rain_summary["basin_accuracy_pct"]
    except Exception as e:
        # The rainfall pipeline failed. Report the stations as UNVERIFIED rather
        # than echoing each prediction back as its own "observation", which would
        # produce a meaningless 100% accuracy.
        log.warning("Station rainfall validation unavailable: %s", e)
        station_volume_accuracy = [
            {
                "station_id": st.get("station_id"),
                "station_name": st.get("station_name", st.get("station_id")),
                "subbasin_id": st.get("subbasin_id", ""),
                "predicted_volume_mm": float(st.get("cumulative_90h_mm", 0.0)),
                "observed_volume_mm": None,
                "source": "UNVERIFIED",
                "error_mm": None,
                "error_pct": None,
                "accuracy_pct": None,
                "status": "UNVERIFIED",
            }
            for st in stations_data
        ]
        basin_rain_error_pct = None
        basin_rain_accuracy_pct = None

    # 7. Scatter Plot Points for Correlation
    scatter_points = []
    for pt in valid_points:
        scatter_points.append({
            "lead_hours": pt["lead_hours"],
            "actual_stage": pt["observed_stage_m"],
            "predicted_stage": pt["predicted_stage_m"],
            # Rating-implied, not independently measured (see compute_pure_metrics).
            "actual_discharge": pt.get("observed_discharge_m3s"),
            "predicted_discharge": pt["predicted_discharge_m3s"],
        })

    # 8. Lead-Time Accuracy Curve (Error by forecast horizon)
    lead_time_decay = []
    windows = [(0, 12, "T+0 to T+12h"), (12, 24, "T+12 to T+24h"),
               (24, 48, "T+24 to T+48h"), (48, 72, "T+48 to T+72h")]
    for w_start, w_end, lbl in windows:
        sub_pts = [p for p in valid_points if w_start <= p["lead_hours"] < w_end]
        if sub_pts:
            sub_pred_s = np.array([p["predicted_stage_m"] for p in sub_pts])
            sub_obs_s = np.array([p["observed_stage_m"] for p in sub_pts])
            sub_rmse, sub_mae = compute_rmse_mae(sub_pred_s, sub_obs_s)
            sub_rho, _ = compute_spearman_correlation(sub_pred_s, sub_obs_s)
            lead_time_decay.append({
                "window": lbl,
                "mae_stage_m": sub_mae,
                "rmse_stage_m": sub_rmse,
                "spearman_rho": sub_rho,
            })

    lifecycle_status = (run_state.get("validation") or {}).get("lifecycle_status")

    return {
        "status": "VALIDATED",
        "lifecycle_status": lifecycle_status or "VALIDATED",
        "verified_hours": len(valid_points),
        "total_forecast_hours": len(shivaji_fc),
        "sample_size_hours": len(valid_points),
        "matched_pairs": len(valid_points),
        "performance_grade": performance_grade,
        "badge_color": badge_color,
        "low_flow_guard": low_flow_guard,
        "metrics": {
            "spearman_rho": spearman_rho_stage,
            "spearman_rho_q": spearman_rho_q,
            "spearman_pval": pval_spearman_stage,
            "pearson_r": r_stage,
            "pearson_r2": r2_stage,
            "nse_stage": nse_stage,
            "nse_discharge": nse_q,
            "rmse_stage_m": rmse_stage,
            "rmse_q_m3s": rmse_q,
            "mae_stage_m": mae_stage,
            "mae_q_m3s": mae_q,
            "pbias_stage_pct": pbias_stage,
            "pbias_discharge_pct": pbias_q,
            "skill_metrics_reliable": bool(nse_reliable),
            "observed_stage_std_m": round(obs_std, 4),
            "baseflow_stage_offset_m": low_flow_guard["baseflow_stage_offset_m"],
            "observed_ungauged_fraction": low_flow_guard["ungauged_fraction"],
            "rating_extrapolated": low_flow_guard["rating_extrapolated"],
            "constant_baseflow_bias": low_flow_guard["constant_bias_detected"],
            "baseflow_note": low_flow_guard["note"],
            "discharge_metrics_source": "RATING_IMPLIED_DERIVED" if pred_q is not None else None,
            "discharge_metrics_note": (
                "Observed discharge is the observed stage pushed through the same "
                "rating curve used for the forecast; it is a derived quantity, not "
                "an independent discharge measurement."
            ),
            "basin_rainfall_accuracy_pct": basin_rain_accuracy_pct,
            "basin_rainfall_error_pct": basin_rain_error_pct,
        },
        "station_volume_accuracy": station_volume_accuracy,
        "scatter_points": scatter_points,
        "lead_time_decay": lead_time_decay,
        "actual_observed_series": actual_obs,
    }

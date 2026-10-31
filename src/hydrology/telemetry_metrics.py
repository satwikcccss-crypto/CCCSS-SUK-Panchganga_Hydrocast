"""
telemetry_metrics.py
====================
Pure statistics and resampling for the ThingSpeak telemetry validator.

Extracted from ``realtime_telemetry_validator.py`` (P1 de-bloat) so the
statistical core — hourly resampling, cycle-id parsing, and NSE/RMSE/PBIAS/
Spearman/Pearson metrics — can be tested without any network, cache, or DB.

It is deliberately free of I/O. ``realtime_telemetry_validator`` re-exports
every public name below, so existing imports keep working unchanged.
"""

from __future__ import annotations

import math
import warnings
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
from scipy import stats

# Elevation of the ultrasonic sensor mount above MSL (metres).
SHIVAJI_DATUM_MSL = 549.35

# ── Validation statistical reliability thresholds ─────────────────────────────
# Correlation and NSE are only meaningful above a minimum sample size. Below
# MIN_CORRELATION_SAMPLES the observed window is too short to rank reliably.
MIN_CORRELATION_SAMPLES = 6
# If the observed series is flatter than this (metres), NSE is numerically
# unstable because its denominator (observed variance) approaches zero and the
# score explodes to large negative values that do not reflect real skill.
MIN_OBS_STAGE_STD_M = 0.05
MIN_OBS_Q_STD_M3S = 1.0
# Observed-variance floor below which NSE is reported as undefined (None)
# rather than a misleading number.
NSE_VARIANCE_FLOOR = 1e-4

def parse_cycle_time(cycle_id: str) -> Optional[datetime]:
    """Parses UTC datetime from a cycle ID formatted as CYC_YYYYMMDD_HHz."""
    try:
        parts = cycle_id.split("_")
        if len(parts) >= 3 and len(parts[1]) == 8:
            date_str = parts[1]
            hour_str = parts[2].rstrip("zZ")
            hour = int(hour_str) if hour_str.isdigit() else 0
            return datetime(
                int(date_str[:4]),
                int(date_str[4:6]),
                int(date_str[6:8]),
                hour,
                0,
                0,
                tzinfo=timezone.utc,
            )
    except Exception:
        pass
    return None


def resample_feeds_hourly(
    feeds: List[Dict[str, Any]],
    datum_msl: float = SHIVAJI_DATUM_MSL,
) -> Dict[str, Dict[str, Any]]:
    """
    Aggregates 5-minute ultrasonic readings into clean hourly mean averages.
    Filters spurious physical outliers (distance outside [15ft, 80ft]).
    """
    hourly_buckets: Dict[str, List[float]] = {}

    for feed in feeds:
        dt_str = feed.get("created_at")
        raw_val = feed.get("field1")
        if not dt_str or raw_val is None:
            continue
        try:
            val_feet = float(raw_val)
            if val_feet < 15.0 or val_feet > 80.0:
                continue
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            hour_key = dt.strftime("%Y-%m-%dT%H:00:00Z")
            hourly_buckets.setdefault(hour_key, []).append(val_feet)
        except (ValueError, TypeError):
            continue

    resampled: Dict[str, Dict[str, Any]] = {}
    for hour_key, feet_list in sorted(hourly_buckets.items()):
        if not feet_list:
            continue
        mean_feet = float(np.mean(feet_list))
        mean_stage_m = round(float(datum_msl - (mean_feet * 0.3048)), 2)
        min_stage_m = round(float(datum_msl - (max(feet_list) * 0.3048)), 2)
        max_stage_m = round(float(datum_msl - (min(feet_list) * 0.3048)), 2)

        resampled[hour_key] = {
            "timestamp": hour_key,
            "observed_stage_m": mean_stage_m,
            "observed_distance_ft": round(mean_feet, 2),
            "sample_count": len(feet_list),
            "min_stage_m": min_stage_m,
            "max_stage_m": max_stage_m,
        }

    return resampled


def compute_pure_metrics(
    pred_stages: np.ndarray,
    obs_stages: np.ndarray,
    pred_discharges: Optional[np.ndarray] = None,
    obs_discharges: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """
    Computes genuine mathematical accuracy metrics on matched pairs:
    Stage (S_sim, S_obs) and Discharge (Q_sim, Q_obs).
    Zero synthetic noise. Zero artificial damping.
    """
    n = len(pred_stages)

    # Error metrics (RMSE / MAE / PBIAS) are well defined for any sample size and
    # are reported whenever at least one matched point exists.
    if n >= 1:
        rmse_s = float(np.sqrt(np.mean((pred_stages - obs_stages) ** 2)))
        mae_s = float(np.mean(np.abs(pred_stages - obs_stages)))
        sum_obs_s = float(np.sum(obs_stages))
        pbias_s = (
            float((np.sum(pred_stages - obs_stages) / sum_obs_s) * 100.0)
            if abs(sum_obs_s) > 1e-6
            else 0.0
        )
    else:
        rmse_s = mae_s = pbias_s = None

    # Skill metrics (NSE / Spearman / Pearson) require both a minimum sample size
    # and enough observed variance to be numerically stable.
    obs_std_s = float(np.std(obs_stages)) if n else 0.0
    nse_is_reliable = (
        n >= MIN_CORRELATION_SAMPLES
        and obs_std_s >= MIN_OBS_STAGE_STD_M
        and float(np.sum((obs_stages - np.mean(obs_stages)) ** 2)) > NSE_VARIANCE_FLOOR
    ) if n else False

    if nse_is_reliable:
        denom_s = float(np.sum((obs_stages - np.mean(obs_stages)) ** 2))
        numer_s = float(np.sum((obs_stages - pred_stages) ** 2))
        nse_s = float(1.0 - (numer_s / denom_s))
    else:
        nse_s = None

    if n >= MIN_CORRELATION_SAMPLES and obs_std_s >= MIN_OBS_STAGE_STD_M:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=getattr(stats, "ConstantInputWarning", UserWarning))
            res_spearman_s = stats.spearmanr(pred_stages, obs_stages)
            rho_s = float(res_spearman_s.statistic) if hasattr(res_spearman_s, "statistic") else float(res_spearman_s[0])
            if math.isnan(rho_s):
                rho_s = 0.0

            res_pearson_s = stats.pearsonr(pred_stages, obs_stages)
            r_val_s = float(res_pearson_s.statistic) if hasattr(res_pearson_s, "statistic") else float(res_pearson_s[0])
            if math.isnan(r_val_s):
                r_val_s = 0.0
            r2_s = r_val_s ** 2
    else:
        rho_s = None
        r2_s = None

    # Discharge metrics. NOTE: the "observed" discharge is the sensor-observed
    # stage pushed through the same rating curve used to build the forecast, so
    # these are rating-implied (derived) values, NOT an independent discharge
    # measurement. They are a monotone transform of the stage errors and must not
    # be read as independent evidence of discharge skill.
    has_q = (
        pred_discharges is not None
        and obs_discharges is not None
        and len(pred_discharges) == n
        and n > 0
    )
    if has_q:
        rmse_q = float(np.sqrt(np.mean((pred_discharges - obs_discharges) ** 2)))
        mae_q = float(np.mean(np.abs(pred_discharges - obs_discharges)))
        sum_obs_q = float(np.sum(obs_discharges))
        pbias_q = (
            float((np.sum(pred_discharges - obs_discharges) / sum_obs_q) * 100.0)
            if abs(sum_obs_q) > 1e-6
            else 0.0
        )

        obs_std_q = float(np.std(obs_discharges))
        if (
            n >= MIN_CORRELATION_SAMPLES
            and obs_std_q >= MIN_OBS_Q_STD_M3S
            and float(np.sum((obs_discharges - np.mean(obs_discharges)) ** 2)) > NSE_VARIANCE_FLOOR
        ):
            denom_q = float(np.sum((obs_discharges - np.mean(obs_discharges)) ** 2))
            numer_q = float(np.sum((obs_discharges - pred_discharges) ** 2))
            nse_q = float(1.0 - (numer_q / denom_q))

            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=getattr(stats, "ConstantInputWarning", UserWarning))
                res_spearman_q = stats.spearmanr(pred_discharges, obs_discharges)
                rho_q = float(res_spearman_q.statistic) if hasattr(res_spearman_q, "statistic") else float(res_spearman_q[0])
                if math.isnan(rho_q):
                    rho_q = 0.0

                res_pearson_q = stats.pearsonr(pred_discharges, obs_discharges)
                r_val_q = float(res_pearson_q.statistic) if hasattr(res_pearson_q, "statistic") else float(res_pearson_q[0])
                if math.isnan(r_val_q):
                    r_val_q = 0.0
                r2_q = r_val_q ** 2
        else:
            nse_q = None
            rho_q = None
            r2_q = None
    else:
        rmse_q = None
        mae_q = None
        nse_q = None
        pbias_q = None
        rho_q = None
        r2_q = None

    # Low-flow representativeness guard. A constant baseflow offset is a
    # datum/anchor bias (not a calibration error) and observed stages below the
    # lowest WRD gauge make the rating an extrapolation. Surfaced explicitly so
    # a ~2 m baseflow bias is never graded as ordinary skill.
    from src.hydrology.stage_converter import assess_low_flow_guard
    low_flow_guard = assess_low_flow_guard(pred_stages, obs_stages)

    # Performance grade. Absolute-error bands (Moriasi et al., 2007) apply ONLY
    # when the skill metrics are reliable. When NSE is unavailable, the grade is
    # driven by the error bands alone and is explicitly labelled as such. A
    # reliably-computed negative NSE is never allowed to grade better than
    # CALIBRATION_REQUIRED.
    if nse_s is not None:
        if nse_s >= 0.75 and rmse_s <= 0.25:
            grade = "EXCELLENT"
        elif nse_s >= 0.60 and rmse_s <= 0.50:
            grade = "VERY_GOOD"
        elif nse_s >= 0.40 and rmse_s <= 1.00:
            grade = "SATISFACTORY"
        elif nse_s > 0.0:
            grade = "MODERATE_BIAS"
        else:
            grade = "CALIBRATION_REQUIRED"
    elif n == 0:
        grade = "ACCUMULATING_TELEMETRY"
    elif obs_std_s < MIN_OBS_STAGE_STD_M:
        # Genuinely stable baseflow: error is meaningful, skill is not defined.
        grade = "BASEFLOW_MISMATCH" if low_flow_guard["constant_bias_detected"] else "BASEFLOW_STABLE"
    else:
        # Not enough matched hours yet to rank the series.
        grade = "ACCUMULATING_TELEMETRY"

    # Validation status. "INSUFFICIENT_DATA" only when there are no matched
    # points at all; a short-but-nonzero window is "ACCUMULATING_TELEMETRY".
    if n == 0:
        status = "INSUFFICIENT_DATA"
    elif nse_is_reliable:
        status = "VALIDATED"
    else:
        status = "ACCUMULATING_TELEMETRY"

    return {
        "status": status,
        "sample_size_hours": n,
        "matched_pairs": n,
        "observed_stage_std_m": round(obs_std_s, 4) if n else None,
        "skill_metrics_reliable": bool(nse_is_reliable),
        "rmse_stage_m": round(rmse_s, 3) if rmse_s is not None else None,
        "mae_stage_m": round(mae_s, 3) if mae_s is not None else None,
        "nse_stage": round(nse_s, 4) if nse_s is not None else None,
        "pbias_stage_pct": round(pbias_s, 2) if pbias_s is not None else None,
        "spearman_rho": round(rho_s, 4) if rho_s is not None else None,
        "pearson_r2": round(r2_s, 4) if r2_s is not None else None,
        "discharge_metrics_source": "RATING_IMPLIED_DERIVED" if has_q else None,
        "discharge_metrics_note": (
            "Observed discharge is derived from the observed stage via the same "
            "rating curve used for the forecast; it is NOT an independent "
            "discharge measurement."
        ),
        "rmse_q_m3s": round(rmse_q, 2) if rmse_q is not None else None,
        "mae_q_m3s": round(mae_q, 2) if mae_q is not None else None,
        "nse_discharge": round(nse_q, 4) if nse_q is not None else None,
        "pbias_discharge_pct": round(pbias_q, 2) if pbias_q is not None else None,
        "spearman_rho_q": round(rho_q, 4) if rho_q is not None else None,
        "pearson_r2_q": round(r2_q, 4) if r2_q is not None else None,
        "baseflow_stage_offset_m": low_flow_guard["baseflow_stage_offset_m"],
        "observed_ungauged_fraction": low_flow_guard["ungauged_fraction"],
        "rating_extrapolated": low_flow_guard["rating_extrapolated"],
        "constant_baseflow_bias": low_flow_guard["constant_bias_detected"],
        "baseflow_note": low_flow_guard["note"],
        "basin_rainfall_accuracy_pct": None,
        "performance_grade": grade,
    }

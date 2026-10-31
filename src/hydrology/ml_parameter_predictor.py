"""
src/hydrology/ml_parameter_predictor.py
========================================
Machine learning model for predicting hydrologic calibration parameters
from full 90-hour observed stage hydrographs.

Uses feature engineering from the entire stage time-series plus
ExtraTreesRegressor for robust parameter prediction.

Key engineered features capture temporal patterns:
  - Rising limb speed (max stage derivative)
  - Falling limb speed
  - Time-to-peak
  - Recession rate
  - Stage variability, duration above thresholds, etc.

The model maps these features to:
  (alpha_k, alpha_lag, delta_cn, muskingum_x)
"""

import json
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    from sklearn.ensemble import ExtraTreesRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_squared_error, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    ExtraTreesRegressor = None  # type: ignore[assignment,misc]
    StandardScaler = None  # type: ignore[assignment,misc]
    train_test_split = None  # type: ignore[assignment]
    mean_squared_error = None  # type: ignore[assignment]
    r2_score = None  # type: ignore[assignment]

try:
    import joblib

    JOBLIB_AVAILABLE = True
except ImportError:  # pragma: no cover - joblib ships with scikit-learn
    joblib = None  # type: ignore[assignment]
    JOBLIB_AVAILABLE = False

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_FILE = PROJECT_ROOT / "data" / "telemetry" / "ml_calibration_state.json"

# Feature engineering config
N_HOURS = 90  # 90-hour forecast window


# ------------------------------------------------------------------
# Feature extraction from full stage hydrograph
# ------------------------------------------------------------------

def extract_stage_features(stage_series: np.ndarray) -> np.ndarray:
    """
    Extract a rich set of features from a 90-hour stage hydrograph.

    Features capture rising/falling patterns, speed, duration, variability.

    Args:
        stage_series: np.ndarray of shape (90,) with stage values (m) at each hour

    Returns:
        np.ndarray of shape (n_features,) with engineered features
    """
    if len(stage_series) != N_HOURS:
        logging.warning("Stage series must be %d hours, got %d", N_HOURS, len(stage_series))
        # Pad or truncate
        if len(stage_series) < N_HOURS:
            padded = np.full(N_HOURS, np.nan, dtype=np.float64)
            padded[:len(stage_series)] = stage_series
            stage_series = padded
        else:
            stage_series = stage_series[:N_HOURS]

    # Impute NaN values
    stage = stage_series.copy()
    mask = np.isnan(stage)
    if np.any(mask):
        # Forward fill
        stage[mask] = np.nan
        # Simple fill: use neighboring values
        for i in range(1, N_HOURS):
            if np.isnan(stage[i]):
                stage[i] = stage[i - 1] if i > 0 and not np.isnan(stage[i - 1]) else stage[i]
        for i in range(N_HOURS - 2, -1, -1):
            if np.isnan(stage[i]):
                stage[i] = stage[i + 1] if i < N_HOURS - 1 and not np.isnan(stage[i + 1]) else stage[i]

    # Ensure numeric
    stage = np.where(np.isnan(stage), 0.0, stage).astype(np.float64)

    features: List[float] = []

    # 1. Basic statistics
    features.append(float(np.mean(stage)))       # mean stage
    features.append(float(np.std(stage)))        # stage std dev
    features.append(float(np.median(stage)))     # median stage
    features.append(float(np.min(stage)))        # min stage
    features.append(float(np.max(stage)))        # max stage
    features.append(float(stage[0]))             # initial stage
    features.append(float(stage[-1]))            # final stage

    # 2. Rise/fall pattern features
    # Compute finite differences (stage rate of change per hour)
    stage_diff = np.diff(stage, prepend=stage[0])

    # Max rate of rise (positive = flooding)
    max_rise_rate = float(np.max(stage_diff)) if len(stage_diff) > 0 else 0.0
    features.append(max_rise_rate)

    # Max rate of fall (negative = receding)
    max_fall_rate = float(np.min(stage_diff)) if len(stage_diff) > 0 else 0.0
    features.append(max_fall_rate)

    # Mean rise rate (positive values only)
    rise_rates = stage_diff[stage_diff > 0]
    mean_rise_rate = float(np.mean(rise_rates)) if len(rise_rates) > 0 else 0.0
    features.append(mean_rise_rate)

    # Mean fall rate (negative values only)
    fall_rates = stage_diff[stage_diff < 0]
    mean_fall_rate = float(np.mean(fall_rates)) if len(fall_rates) > 0 else 0.0
    features.append(mean_fall_rate)

    # 3. Time-to-peak and peak timing
    peak_stage = float(np.max(stage))
    peak_idx = int(np.argmax(stage))
    features.append(float(peak_idx))          # time-to-peak in hours
    features.append(float(peak_stage))        # peak stage

    # 4. Recession characteristics
    # Find points after peak where stage is receding
    after_peak = stage[peak_idx:]
    if len(after_peak) > 1:
        # Recession rate from peak to end
        recession_total = float(after_peak[0] - after_peak[-1])
        recession_rate = recession_total / len(after_peak) if len(after_peak) > 0 else 0.0
        features.append(recession_rate)
    else:
        features.append(0.0)
        features.append(0.0)

    # 5. Duration above thresholds
    # Count hours above various quantiles
    q75 = float(np.percentile(stage, 75))
    q90 = float(np.percentile(stage, 90))
    hours_above_75 = int(np.sum(stage > q75))
    hours_above_90 = int(np.sum(stage > q90))
    features.append(float(hours_above_75))
    features.append(float(hours_above_90))

    # 6. Stage range and variability
    stage_range = float(np.ptp(stage))  # peak-to-peak
    features.append(stage_range)
    features.append(float(np.var(stage)))      # variance
    features.append(float(np.nanmean([np.stats.skew(stage)])[0]) if len(stage) > 2 and hasattr(np, 'stats') and hasattr(np.stats, 'skew') else 0.0)  # skewness

    # 7. Integral of stage (cumulative exposure)
    cumulative_stage = float(np.sum(stage))
    features.append(cumulative_stage)

    # 8. Rise time: hours from start to reach 90% of peak range
    range_90 = 0.9 * (float(np.max(stage)) - float(np.min(stage)))
    rise_start = float(np.min(stage))
    for i in range(N_HOURS):
        if stage[i] >= rise_start + range_90:
            features.append(float(i))  # hours to reach 90% of range
            break
    else:
        features.append(float(N_HOURS))  # never reached

    # 9. Fall time: hours from peak to reach 50% down
    fall_range = 0.5 * (float(np.max(stage)) - float(np.min(stage)))
    fall_from_peak = float(np.max(stage)) - fall_range
    fall_hours = 0
    for i in range(peak_idx, N_HOURS):
        if stage[i] <= fall_from_peak:
            fall_hours = i - peak_idx
            break
    features.append(float(fall_hours))

    # 10. Ratio of rise to total duration
    features.append(float(peak_idx) / N_HOURS if N_HOURS > 0 else 0.0)

    # 11. Stage acceleration (second derivative)
    if len(stage_diff) > 1:
        stage_accel = np.diff(stage_diff)
        features.append(float(np.max(stage_accel)))
        features.append(float(np.min(stage_accel)))
        features.append(float(np.mean(stage_accel)))
    else:
        features.extend([0.0, 0.0, 0.0])

    # 12. Hours in different stage bands
    # Low flow: below 50th percentile
    # Medium flow: 50th-80th percentile
    # High flow: above 80th percentile
    q50 = float(np.percentile(stage, 50))
    q80 = float(np.percentile(stage, 80))
    hours_low = float(np.sum(stage < q50))
    hours_med = float(np.sum((stage >= q50) & (stage < q80)))
    hours_high = float(np.sum(stage >= q80))
    features.append(hours_low / N_HOURS)
    features.append(hours_med / N_HOURS)
    features.append(hours_high / N_HOURS)

    return np.array(features, dtype=np.float64)


# ------------------------------------------------------------------
# Main predictor class
# ------------------------------------------------------------------

class HydrologicParameterPredictor:
    """
    ML predictor for hydrologic calibration parameters based on historical
    discrepancy-to-parameter mappings from real-time recalibration events.

    Uses ExtraTreesRegressor with engineered features from full 90-hour
    stage hydrographs to capture rising/falling flood patterns.

    Can predict from either:
      1. Full 90-hour stage series (new): engineer features capturing rise/fall patterns
      2. Discrepancy summary (old/backward-compat): timing_offset, stage_error, peak_error
    """

    def __init__(self, retrain_on_load: bool = True):
        self.model: Optional[Any] = None
        self.scaler_X = StandardScaler() if SKLEARN_AVAILABLE else None
        self.scaler_y = StandardScaler() if SKLEARN_AVAILABLE else None
        self.is_trained = False
        self.training_history: List[Dict] = []

        self._model_path = PROJECT_ROOT / "data" / "telemetry" / "ml_parameter_model_et.joblib"
        self._scaler_X_path = PROJECT_ROOT / "data" / "telemetry" / "ml_parameter_scaler_X.json"
        self._scaler_y_path = PROJECT_ROOT / "data" / "telemetry" / "ml_parameter_scaler_y.json"
        self._validation_path = PROJECT_ROOT / "data" / "telemetry" / "ml_parameter_validation.json"

        # SAFETY GATE: a fitted model is never trusted for operational use until
        # an explicit backtest has marked it validated. Until then `predict()`
        # returns None and the caller falls back to the deterministic physics
        # prior — an unvalidated model must never steer life-safety parameters.
        self.validation_passed = False
        self.validation_info: Dict[str, Any] = {}
        self._load_validation()

        if not SKLEARN_AVAILABLE:
            log.warning("scikit-learn is not installed; HydrologicParameterPredictor operating in fallback mode")
            return

        if retrain_on_load:
            self._load_or_train()

    # ... (keep the rest of the class the same, but update predict() to support both interfaces)

    # ------------------------------------------------------------------
    # Data extraction from calibration state
    # ------------------------------------------------------------------

    def _extract_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extracts X (engineered features from stage series) and y (parameters)
        from the calibration state history.

        Returns:
            X: np.ndarray of shape (n_samples, n_features)
            y: np.ndarray of shape (n_samples, 4) - (alpha_k, alpha_lag, delta_cn, muskingum_x)
        """
        if not STATE_FILE.exists():
            log.warning("Calibration state file not found at %s", STATE_FILE)
            return np.array([]), np.array([])

        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception as e:
            log.error("Failed to load calibration state: %s", e)
            return np.array([]), np.array([])

        history = state.get("history", [])
        if not history:
            log.warning("No calibration history found in state file")
            return np.array([]), np.array([])

        X_list: List[np.ndarray] = []
        y_list: List[List[float]] = []

        for entry in history:
            # Prefer the OBSERVED hydrograph (list of floats) written by the
            # calibrator; fall back to a legacy `forecast_series` of point dicts.
            observed_series = entry.get("observed_series")
            if observed_series:
                stage_series = np.array(
                    [np.nan if v is None else float(v) for v in observed_series],
                    dtype=np.float64,
                )
            else:
                forecast_series = entry.get("forecast_series", [])
                if not forecast_series or len(forecast_series) < 10:
                    log.debug(
                        "Entry skipped: no usable hydrograph "
                        "(observed_series/forecast_series missing or short)",
                    )
                    continue
                stage_series = np.array([
                    pt.get("stage_m") if pt.get("stage_m") is not None else np.nan
                    for pt in forecast_series
                ], dtype=np.float64)

            if np.all(np.isnan(stage_series)) or len(stage_series) < 5:
                log.debug("Entry skipped: insufficient valid stage data")
                continue

            # Engineer features from the full stage series
            features = extract_stage_features(stage_series)

            X_list.append(features)

            # Extract calibrated parameters (targets)
            alpha_k = entry.get("alpha_k", 1.0)
            alpha_lag = entry.get("alpha_lag", 1.0)
            delta_cn = entry.get("delta_cn", 0.0)
            muskingum_x = entry.get("muskingum_x", 0.25)

            y_list.append([alpha_k, alpha_lag, delta_cn, muskingum_x])

        if not X_list:
            log.warning("No valid training entries with stage series found")
            return np.array([]), np.array([])

        X = np.array(X_list, dtype=np.float64)
        y = np.array(y_list, dtype=np.float64)

        # Log feature count
        n_features = X.shape[1] if X.ndim > 1 else 1
        log.info(
            "Extracted %d training samples with %d features each",
            len(X), n_features,
        )
        return X, y

    # ------------------------------------------------------------------
    # Training / loading
    # ------------------------------------------------------------------

    def _load_or_train(self) -> None:
        """Loads existing model/scalers if present, otherwise trains from history."""
        # Try to load pretrained model
        if self._model_exists():
            self._load_pretrained()
            log.info("Loaded pretrained ML parameter predictor (model: %s)", self.model is not None)
            return

        # Train from historical calibration data
        if not SKLEARN_AVAILABLE:
            log.warning("scikit-learn is not installed; cannot train ML model")
            return

        X, y = self._extract_training_data()
        if X.shape[0] == 0 or y.shape[0] == 0 or X.shape[0] < 3:
            log.warning(
                "Insufficient training data (%d samples); predictor will operate in fallback mode",
                X.shape[0],
            )
            return

        # Train-test split for validation
        X_train, X_valid, y_train, y_valid = train_test_split(
            X, y, test_size=0.25, random_state=42, shuffle=True,
        )

        # Scale features and targets
        X_train_scaled = self.scaler_X.fit_transform(X_train)
        X_valid_scaled = self.scaler_X.transform(X_valid)
        y_train_scaled = self.scaler_y.fit_transform(y_train)
        y_valid_scaled = self.scaler_y.transform(y_valid)

        # Train ExtraTrees model (robust random forest variant)
        self.model = ExtraTreesRegressor(
            n_estimators=200,
            max_depth=None,
            random_state=42,
            n_jobs=-1,
            verbose=0,
        )
        self.model.fit(X_train_scaled, y_train_scaled)

        # Evaluate
        y_pred_scaled = self.model.predict(X_valid_scaled)
        rmse = float(np.sqrt(mean_squared_error(y_valid_scaled, y_pred_scaled)))
        r2 = float(r2_score(y_valid_scaled, y_pred_scaled))

        # Inverse transform metrics back to original scale for logging
        y_pred_orig = self.scaler_y.inverse_transform(y_pred_scaled)
        y_valid_orig = self.scaler_y.inverse_transform(y_valid_scaled)
        rmse_orig = float(np.sqrt(mean_squared_error(y_valid_orig, y_pred_orig)))
        r2_orig = float(r2_score(y_valid_orig, y_pred_orig))

        log.info(
            "ML predictor trained: ExtraTrees | n_estimators=200 | "
            "RMSE=%.3f (orig) / %.3f (scaled) | R²=%.3f (orig) / %.3f (scaled)",
            rmse_orig, rmse, r2_orig, r2,
        )

        # Log feature importances
        importances = self.model.feature_importances_
        feature_names = [
            "mean_stage", "std_stage", "median_stage", "min_stage", "max_stage",
            "initial_stage", "final_stage", "max_rise_rate", "max_fall_rate",
            "mean_rise_rate", "mean_fall_rate", "peak_time_hrs", "peak_stage",
            "recession_rate", "hours_above_75pct", "hours_above_90pct",
            "stage_range", "stage_var", "skew", "cumulative_stage",
            "rise_time_hrs", "fall_time_hrs", "rise_fraction",
            "accel_max", "accel_min", "accel_mean",
            "frac_low_flow", "frac_med_flow", "frac_high_flow",
        ]
        # Only log importances for features we actually have
        n_log = min(len(feature_names), len(importances))
        importance_pairs = list(zip(feature_names[:n_log], importances[:n_log]))
        sorted_importance = sorted(importance_pairs, key=lambda x: x[1], reverse=True)
        log.info("Top 5 feature importances:")
        for name, imp in sorted_importance[:5]:
            log.info("  %s: %.4f", name, imp)

        self.is_trained = True
        self._save_pretrained()

        log.info(
            "ML predictor trained successfully with %d historical events",
            len(X),
        )

    def _model_exists(self) -> bool:
        """Checks whether pretrained model and scalers exist on disk."""
        return (
            self._model_path.exists()
            and self._scaler_X_path.exists()
            and self._scaler_y_path.exists()
        )

    def _load_pretrained(self) -> None:
        """Loads model and scalers from disk.

        The estimator is persisted with joblib so the ACTUAL fitted trees
        survive a restart. The previous implementation round-tripped only
        metadata (feature importances) and rebuilt an unfitted estimator, which
        both discarded the model and crashed on the injected read-only
        ``feature_importances_`` property — so a "loaded" model could never
        predict, and the failure was swallowed silently.
        """
        if not SKLEARN_AVAILABLE:
            self.is_trained = False
            self.model = None
            return

        try:
            if not JOBLIB_AVAILABLE:
                raise RuntimeError("joblib unavailable; cannot load persisted estimator")

            model = joblib.load(self._model_path)
            # Guard: only accept a genuinely fitted estimator.
            if not hasattr(model, "estimators_"):
                raise ValueError(
                    "persisted estimator is not fitted (missing `estimators_`); refusing to load"
                )
            self.model = model

            with open(self._scaler_X_path, "r", encoding="utf-8") as f:
                self.scaler_X = self._deserialize_scaler(json.load(f))
            with open(self._scaler_y_path, "r", encoding="utf-8") as f:
                self.scaler_y = self._deserialize_scaler(json.load(f))

            self.is_trained = True
            log.info("Loaded pretrained model: %s", self.model.__class__.__name__)
        except Exception as e:
            # Loud, not silent: an unloadable model is a real operational fault.
            log.error(
                "Failed to load pretrained model (%s); predictor stays in physics-fallback", e
            )
            self.is_trained = False
            self.model = None

    def _save_pretrained(self) -> None:
        """Persists the fitted estimator (joblib) and scalers (JSON) to disk."""
        try:
            if self.model is None or not JOBLIB_AVAILABLE:
                log.warning("Model not fitted or joblib unavailable; skipping persistence")
                return

            self._model_path.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(self.model, self._model_path)

            with open(self._scaler_X_path, "w", encoding="utf-8") as f:
                json.dump(self._serialize_scaler(self.scaler_X), f, indent=2)

            with open(self._scaler_y_path, "w", encoding="utf-8") as f:
                json.dump(self._serialize_scaler(self.scaler_y), f, indent=2)

            log.info("Saved pretrained ML parameter predictor to disk")
        except Exception as e:
            log.warning("Failed to save pretrained model: %s", e)

    # ------------------------------------------------------------------
    # Validation gate & serialization helpers
    # ------------------------------------------------------------------

    def _load_validation(self) -> None:
        """Loads the backtest verdict. ``passed`` defaults to False."""
        try:
            if self._validation_path.exists():
                with open(self._validation_path, "r", encoding="utf-8") as f:
                    info = json.load(f)
                self.validation_info = info if isinstance(info, dict) else {}
                self.validation_passed = bool(self.validation_info.get("passed", False))
        except Exception as e:
            log.warning("Failed to load ML validation verdict: %s", e)
            self.validation_info = {}
            self.validation_passed = False

    def mark_validated(self, passed: bool, **metrics: Any) -> None:
        """Records an explicit backtest verdict for the persisted model.

        Only a ``passed=True`` verdict allows the model to influence the
        calibration. This switch keeps an unvalidated model out of the
        life-safety path.
        """
        self.validation_passed = bool(passed)
        self.validation_info = {"passed": bool(passed), **metrics}
        try:
            self._validation_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._validation_path, "w", encoding="utf-8") as f:
                json.dump(self.validation_info, f, indent=2)
        except Exception as e:
            log.warning("Failed to persist ML validation verdict: %s", e)
        log.info("ML predictor validation set to %s", "PASSED" if passed else "REJECTED")

    def get_status(self) -> Dict[str, Any]:
        """Honest, machine-readable status of the ML predictor."""
        if not SKLEARN_AVAILABLE:
            state = "SKLEARN_UNAVAILABLE"
        elif not self.is_trained or self.model is None:
            state = "UNTRAINED"
        elif not self.validation_passed:
            state = "TRAINED_UNVALIDATED"
        else:
            state = "VALIDATED"
        return {
            "state": state,
            "is_trained": self.is_trained,
            "validation_passed": self.validation_passed,
            "validation_info": self.validation_info,
            "contributes_to_calibration": bool(
                SKLEARN_AVAILABLE and self.is_trained and self.validation_passed
            ),
        }

    # ------------------------------------------------------------------
    # Scaler serialization helpers
    # ------------------------------------------------------------------

    def _serialize_scaler(self, scaler):
        """Serializes a StandardScaler."""
        return {
            "scale": scaler.scale_.tolist(),
            "mean": scaler.mean_.tolist(),
            "n_features": scaler.n_features_in_,
        }

    def _deserialize_scaler(self, data: Dict):
        """Restores a StandardScaler from JSON."""
        if not SKLEARN_AVAILABLE or StandardScaler is None:
            return None
        scaler = StandardScaler()
        scaler.scale_ = np.array(data.get("scale", [1.0] * 25))
        scaler.mean_ = np.array(data.get("mean", [0.0] * 25))
        scaler.n_features_in_ = data.get("n_features", 25)
        return scaler

    # ------------------------------------------------------------------
    # Public prediction API
    # ------------------------------------------------------------------

    def predict(
        self,
        stage_series: Optional[np.ndarray] = None,
        timing_offset_hours: Optional[float] = None,
        stage_discrepancy_m: Optional[float] = None,
        peak_discharge_error_m3s: Optional[float] = None,
    ) -> Optional[Dict[str, float]]:
        """
        Predicts calibration parameters from an OBSERVED 90-hour stage hydrograph.

        Only a genuine stage hydrograph is accepted as a model input. The
        previous "discrepancy summary" interface stuffed Δt / Δh / ΔQ into slots
        the model interprets as mean / std / median stage — a semantic mismatch
        that would emit garbage predictions the moment the model trained — so it
        has been removed. The discrepancy kwargs are kept only so existing call
        sites do not break; they are logged and ignored.

        The model is consulted ONLY when it is both fitted and backtest-validated;
        otherwise None is returned and the caller uses the deterministic physics
        prior. This is a life-safety gate.

        Args:
            stage_series: np.ndarray of shape (90,) with OBSERVED stage (m MSL).
            timing_offset_hours: Accepted for backwards compatibility; not used as model input.
            stage_discrepancy_m: Accepted for backwards compatibility; not used as model input.
            peak_discharge_error_m3s: Accepted for backwards compatibility; not used as model input.

        Returns:
            Dict(alpha_k, alpha_lag, delta_cn, muskingum_x) or None.
        """
        if timing_offset_hours is not None or stage_discrepancy_m is not None or peak_discharge_error_m3s is not None:
            log.debug("predict(): discrepancy kwargs are ignored; only stage_series is used")

        status = self.get_status()
        if not status["contributes_to_calibration"]:
            log.info(
                "ML predictor not used (state=%s); caller falls back to physics prior",
                status["state"],
            )
            return None

        if stage_series is None:
            log.warning("predict() requires an observed stage_series; returning None")
            return None

        # Ensure 90 points
        if len(stage_series) != N_HOURS:
            log.warning(
                "Stage series must be %d hours, got %d; will pad/truncate",
                N_HOURS, len(stage_series),
            )
            if len(stage_series) < N_HOURS:
                padded = np.full(N_HOURS, np.nan, dtype=np.float64)
                padded[: len(stage_series)] = stage_series
                stage_series = padded
            else:
                stage_series = stage_series[:N_HOURS]

        # Engineer features from the full observed stage series
        features = extract_stage_features(stage_series)
        features_scaled = self.scaler_X.transform(features.reshape(1, -1))[0]

        # Predict
        y_scaled = self.model.predict(features_scaled.reshape(1, -1))[0]
        y_orig = self.scaler_y.inverse_transform(y_scaled.reshape(1, -1))[0]

        return {
            "alpha_k": float(y_orig[0]),
            "alpha_lag": float(y_orig[1]),
            "delta_cn": float(y_orig[2]),
            "muskingum_x": float(y_orig[3]),
        }

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def get_feature_importances(self) -> Optional[Dict[str, float]]:
        """Returns feature importance mapping for the current model."""
        if not self.is_trained or self.model is None:
            return None
        import numpy as np
        importances = self.model.feature_importances_
        feature_names = [
            "mean_stage", "std_stage", "median_stage", "min_stage", "max_stage",
            "initial_stage", "final_stage", "max_rise_rate", "max_fall_rate",
            "mean_rise_rate", "mean_fall_rate", "peak_time_hrs", "peak_stage",
            "recession_rate", "hours_above_75pct", "hours_above_90pct",
            "stage_range", "stage_var", "skew", "cumulative_stage",
            "rise_time_hrs", "fall_time_hrs", "rise_fraction",
            "accel_max", "accel_min", "accel_mean",
            "frac_low_flow", "frac_med_flow", "frac_high_flow",
        ]
        n_features = len(feature_names)
        importances_truncated = importances[:n_features] if len(importances) >= n_features else np.pad(
            importances, (0, n_features - len(importances)), constant_values=0,
        )
        return {name: float(imp) for name, imp in zip(feature_names, importances_truncated)}

    def get_training_sample_count(self) -> int:
        """Returns the number of historical calibration events used for training."""
        if not STATE_FILE.exists():
            return 0
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
            return len(state.get("history", []))
        except Exception:
            return 0
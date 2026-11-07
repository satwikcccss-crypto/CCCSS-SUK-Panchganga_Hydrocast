"""
backend/hydrology/__init__.py
==============================
Backward-compatible re-exports for the legacy ``backend.hydrology`` namespace.

During the Windows Server production alignment, several modules moved out of
``backend/hydrology/`` into their own domains:

    stage_converter      -> backend.stage_conversion.stage_converter
    rating_physics       -> backend.hydraulics.rating_physics
    ml_calibration       -> backend.ml.ml_calibration
    ml_parameter_predictor -> backend.ml.ml_parameter_predictor
    telemetry_metrics    -> backend.validation.telemetry_metrics
    realtime_telemetry_validator -> backend.validation.realtime_telemetry_validator
    validation_metrics   -> backend.validation.validation_metrics
    post_process         -> backend.stage_conversion.post_process

This shim re-exports the public API so legacy test imports keep working.
"""

from backend.stage_conversion.stage_converter import (  # noqa: F401
    convert_discharge_to_stage_manning,
    convert_stage_to_discharge_manning,
    WRD_MONSOON_BASEFLOW_FLOOR_M3S,
)
from backend.hydraulics.rating_physics import (  # noqa: F401
    station_from_points,
    wetted_properties,
)
from backend.ml.ml_calibration import (  # noqa: F401
    calibrator,
    calculate_peak_arrival_window,
    AdaptiveHydrologicCalibrator,
    BASE_SUB_MODELS,
    BASE_REACHES,
)
from backend.ml.ml_parameter_predictor import (  # noqa: F401
    HydrologicParameterPredictor,
)
from backend.validation.telemetry_metrics import (  # noqa: F401
    SHIVAJI_DATUM_MSL,
    MIN_CORRELATION_SAMPLES,
    MIN_OBS_Q_STD_M3S,
    MIN_OBS_STAGE_STD_M,
    NSE_VARIANCE_FLOOR,
)
from backend.validation.validation_metrics import (  # noqa: F401
    evaluate_forecast_accuracy,
)
from backend.validation.realtime_telemetry_validator import (  # noqa: F401
    validate_active_cycle,
    load_telemetry_cache,
)
from backend.hydrology.runs_tracker import (  # noqa: F401
    RUNS_DIR,
    _run_path,
    get_computation_run,
    save_computation_run,
    list_computation_runs,
)

# ── Module-level backward-compatible aliases ──────────────────────────────────
# Tests import whole modules from backend.hydrology; re-export them here.
from backend.stage_conversion import stage_converter as stage_converter  # noqa: F401
from backend.stage_conversion import post_process as post_process  # noqa: F401
from backend.ml import ml_calibration as ml_calibration  # noqa: F401
from backend.validation import realtime_telemetry_validator as realtime_telemetry_validator  # noqa: F401
from backend.validation import telemetry_metrics as telemetry_metrics  # noqa: F401
from backend.stage_conversion import stage_converter as stage_converter  # noqa: F401
from backend.ml import ml_parameter_predictor as ml_parameter_predictor  # noqa: F401

__all__ = [
    "convert_discharge_to_stage_manning",
    "convert_stage_to_discharge_manning",
    "WRD_MONSOON_BASEFLOW_FLOOR_M3S",
    "station_from_points",
    "wetted_properties",
    "calibrator",
    "calculate_peak_arrival_window",
    "AdaptiveHydrologicCalibrator",
    "BASE_SUB_MODELS",
    "BASE_REACHES",
    "HydrologicParameterPredictor",
    "SHIVAJI_DATUM_MSL",
    "MIN_CORRELATION_SAMPLES",
    "MIN_OBS_Q_STD_M3S",
    "MIN_OBS_STAGE_STD_M",
    "NSE_VARIANCE_FLOOR",
    "evaluate_forecast_accuracy",
    "validate_active_cycle",
    "load_telemetry_cache",
    "RUNS_DIR",
    "_run_path",
    "get_computation_run",
    "save_computation_run",
    "list_computation_runs",
]

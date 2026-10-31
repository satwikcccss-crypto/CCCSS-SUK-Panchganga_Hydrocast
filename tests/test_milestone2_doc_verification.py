"""Milestone 2 Documentation-to-Source Empirical Verification Test Suite.

Adversarial empirical challenge harness validating:
1. System 1 (Dual-Engine / Python Twin): Symbols, functions, and formulas in docs/hec-hms-engine.md and docs/python-twin-emulator.md physically exist in src/hms/runner.py.
2. System 2 (Adaptive ML Calibrator): Classes, methods, and parameters in docs/ml-calibration-engine.md and docs/api-reference/calibration.md exist in src/hydrology/ml_calibration.py and ml_parameter_predictor.py.
3. System 3 (Database Schema): All 13 tables and 7 views documented in docs/database.md exist verbatim in database/supabase_schema.sql.
4. System 4 (API Security & Limits): Security functions, key variables, and rate limiters in docs/api-reference/security.md exist in src/api/security.py, keys.py, limits.py.
5. System 5 (Real-Time Telemetry & Metrics): Sensors, thresholds, cache paths, and metric functions in docs/iot-telemetry.md exist in src/hydrology/realtime_telemetry_validator.py and telemetry_metrics.py.
6. System 6 (HydroSim 2D Handoff): Multi-route endpoints and query parameters in docs/integration-hydrosim.md exist in src/api/main.py.
7. System 7 (Rating Physics & PCHIP): Functions, surveyed bed levels, and anchor tables in docs/stage-discharge-conversion.md and docs/hydraulics.md exist in src/hydrology/rating_physics.py and stage_converter.py.
8. System 8 (Test Architecture): All test modules listed in docs/deployment-operations.md exist on disk in tests/.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import List, Set

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
SRC_DIR = REPO_ROOT / "src"
DB_FILE = REPO_ROOT / "database" / "supabase_schema.sql"


class TestSystem1DualEngineDocumentation:
    """Validate System 1 (HEC-HMS Engine & Python Twin Emulator)."""

    def test_runner_symbols_exist(self) -> None:
        import src.hms.runner as runner

        expected_funcs = [
            "find_hec_hms",
            "patch_control_spec",
            "snapshot_control_spec",
            "restore_control_spec",
            "write_jython_script",
            "classify_amc",
            "route_muskingum",
            "compute_emulator_hydrograph",
            "derive_baseflow_m3s",
            "execute_hec_hms",
        ]
        for fn_name in expected_funcs:
            assert hasattr(runner, fn_name), f"Expected function {fn_name} missing from src/hms/runner.py"

    def test_python_twin_emulator_doc_contains_real_identifiers(self) -> None:
        doc = (DOCS_DIR / "python-twin-emulator.md").read_text(encoding="utf-8")
        assert "compute_emulator_hydrograph" in doc
        assert "route_muskingum" in doc
        assert "AMC-I" in doc and "AMC-II" in doc and "AMC-III" in doc
        assert "k_lim_hi" in doc
        assert "k_lim_lo" in doc
        assert "WARNING 41169" in doc
        assert "test_golden_emulator.py" in doc

    def test_hec_hms_engine_doc_differentiates_dual_engines(self) -> None:
        doc = (DOCS_DIR / "hec-hms-engine.md").read_text(encoding="utf-8")
        assert "compute_emulator_hydrograph" in doc
        assert "compute.jy" in doc
        assert "Control_1.control" in doc


class TestSystem2AdaptiveCalibratorDocumentation:
    """Validate System 2 (Physics-Informed Adaptive Calibrator & ML Predictor)."""

    def test_calibrator_classes_and_methods_exist(self) -> None:
        from src.hydrology.ml_calibration import AdaptiveHydrologicCalibrator
        from src.hydrology.ml_parameter_predictor import HydrologicParameterPredictor

        calib_methods = [
            "detect_timing_and_stage_discrepancy",
            "recalibrate_parameters",
            "sync_to_hec_hms_basin",
            "load_calibration_state",
            "save_calibration_state",
        ]
        for m in calib_methods:
            assert hasattr(AdaptiveHydrologicCalibrator, m), f"Method {m} missing from AdaptiveHydrologicCalibrator"

        pred_methods = [
            "predict",
            "mark_validated",
            "get_status",
            "get_feature_importances",
        ]
        for m in pred_methods:
            assert hasattr(HydrologicParameterPredictor, m), f"Method {m} missing from HydrologicParameterPredictor"

    def test_calibrator_doc_reflects_code_parameters(self) -> None:
        doc = (DOCS_DIR / "ml-calibration-engine.md").read_text(encoding="utf-8")
        api_ref = (DOCS_DIR / "api-reference" / "calibration.md").read_text(encoding="utf-8")
        both_docs = doc + "\n" + api_ref

        # Verify narrative page documents methods, parameters, and algorithms
        assert "Physics-Informed Adaptive Hydrologic Calibrator" in doc
        assert "HydrologicParameterPredictor" in doc
        assert "detect_timing_and_stage_discrepancy" in both_docs
        assert "recalibrate_parameters" in both_docs
        assert "sync_to_hec_hms_basin" in both_docs
        assert "scipy.optimize.least_squares" in doc
        assert "alpha_K" in doc or r"\alpha_K" in doc
        assert "alpha_lag" in doc or r"\alpha_{lag}" in doc
        assert "Delta_CN" in doc or r"\Delta CN" in doc
        assert "UNTRAINED" in doc
        assert "TRAINED_UNVALIDATED" in doc
        assert "VALIDATED" in doc

        # Verify API reference registers the python module for mkdocstrings reflection
        assert "src.hydrology.ml_calibration" in api_ref
        assert "src.hydrology.ml_parameter_predictor" in api_ref


class TestSystem3DatabaseSchemaDocumentation:
    """Validate System 3 (PostgreSQL / PostGIS Database Schema)."""

    def test_all_13_tables_and_7_views_exist_in_sql_and_docs(self) -> None:
        assert DB_FILE.is_file(), "database/supabase_schema.sql missing"
        sql_content = DB_FILE.read_text(encoding="utf-8")
        doc_content = (DOCS_DIR / "database.md").read_text(encoding="utf-8")

        expected_tables = [
            "subbasins",
            "gauge_stations",
            "bridge_sites",
            "simulation_runs",
            "forecast_validation_metrics",
            "station_rainfall_telemetry",
            "hydrograph_results",
            "peak_discharge_events",
            "runoff_summary",
            "bridge_stage_forecast",
            "wrd_field_benchmarks",
            "pipeline_step_log",
            "alert_events",
        ]

        expected_views = [
            "v_model_accuracy_summary",
            "v_bridge_alert_summary",
            "v_historical_runs_ledger",
            "v_latest_hydrograph",
            "v_latest_peak_summary",
            "v_active_alerts_enriched",
            "v_cycle_performance",
        ]

        for tbl in expected_tables:
            assert re.search(rf"CREATE TABLE IF NOT EXISTS (?:public\.)?{tbl}\b", sql_content, re.IGNORECASE), (
                f"Table {tbl} not found in database/supabase_schema.sql"
            )
            assert f"`{tbl}`" in doc_content or f" {tbl} " in doc_content, (
                f"Table {tbl} not documented in docs/database.md"
            )

        for vw in expected_views:
            assert re.search(rf"CREATE (?:OR REPLACE )?VIEW (?:public\.)?{vw}\b", sql_content, re.IGNORECASE), (
                f"View {vw} not found in database/supabase_schema.sql"
            )
            assert f"`{vw}`" in doc_content or f" {vw} " in doc_content, (
                f"View {vw} not documented in docs/database.md"
            )

    def test_postgis_and_extensions_schema_documented(self) -> None:
        sql = DB_FILE.read_text(encoding="utf-8")
        doc = (DOCS_DIR / "database.md").read_text(encoding="utf-8")
        assert "CREATE SCHEMA IF NOT EXISTS extensions" in sql
        assert "extensions" in doc
        assert "postgis" in doc.lower()


class TestSystem4SecurityAndRateLimitingDocumentation:
    """Validate System 4 (API Security, Dual-Tier Keys & Rate Limiting)."""

    def test_security_and_keys_symbols_exist(self) -> None:
        import src.api.security as security
        import src.api.keys as keys
        import src.api.limits as limits

        for fn in ["hash_password", "verify_password", "verify_admin_credentials", "create_access_token", "decode_access_token", "verify_admin_auth"]:
            assert hasattr(security, fn), f"Symbol {fn} missing from src/api/security.py"

        for fn in ["consumer_keys", "verify_consumer_key", "verify_public_key"]:
            assert hasattr(keys, fn), f"Symbol {fn} missing from src/api/keys.py"

        assert hasattr(limits, "limiter"), "limiter missing from src/api/limits.py"
        assert hasattr(limits, "RATE_LIMIT_PUBLIC"), "RATE_LIMIT_PUBLIC missing from src/api/limits.py"

    def test_security_doc_matches_implementation(self) -> None:
        doc = (DOCS_DIR / "api-reference" / "security.md").read_text(encoding="utf-8")
        assert "verify_consumer_key" in doc
        assert "consumer_keys" in doc
        assert "CONSUMER_API_KEYS" in doc
        assert "HYDROCAST_READONLY_KEY" in doc
        assert "hmac.compare_digest" in doc
        assert "HS256" in doc
        assert "verify_admin_credentials" in doc
        assert "bcrypt" in doc.lower()


class TestSystem5RealTimeTelemetryDocumentation:
    """Validate System 5 (ThingSpeak Ingestion & Telemetry Metrics)."""

    def test_validator_and_metrics_functions_exist(self) -> None:
        import src.hydrology.realtime_telemetry_validator as validator
        import src.hydrology.telemetry_metrics as metrics

        for fn in ["fetch_thingspeak_feeds", "load_telemetry_cache", "save_telemetry_cache", "validate_run_with_observations", "sync_validation_to_storage_and_db"]:
            assert hasattr(validator, fn), f"Function {fn} missing from realtime_telemetry_validator.py"

        for fn in ["resample_feeds_hourly", "compute_pure_metrics", "parse_cycle_time"]:
            assert hasattr(metrics, fn), f"Function {fn} missing from telemetry_metrics.py"

    def test_iot_telemetry_doc_matches_physics_and_metrics(self) -> None:
        doc = (DOCS_DIR / "iot-telemetry.md").read_text(encoding="utf-8")
        assert "3424513" in doc  # ThingSpeak channel
        assert "549.35" in doc   # Bridge sensor datum
        assert "resample_feeds_hourly" in doc
        assert "15.0" in doc and "80.0" in doc  # Physical filter bounds
        assert "RMSE" in doc
        assert "MAE" in doc
        assert "NSE" in doc
        assert "PBIAS" in doc


class TestSystem6HydroSim2DHandoffDocumentation:
    """Validate System 6 (HydroSim 2D Boundary Condition Export)."""

    def test_water_level_routes_exist_in_api(self) -> None:
        main_py = (SRC_DIR / "api" / "main.py").read_text(encoding="utf-8")
        required_routes = [
            "/api/v1/hydrocast/water-levels",
            "/api/v1/water-levels",
            "/api/v1/hydrosim/water-levels",
            "/api/v1/integration/hydrosim/stage",
        ]
        for route in required_routes:
            assert route in main_py, f"Route {route} not found in src/api/main.py"

    def test_hydrosim_handoff_doc_matches_api(self) -> None:
        doc = (DOCS_DIR / "integration-hydrosim.md").read_text(encoding="utf-8")
        assert "/api/v1/hydrocast/water-levels" in doc
        assert "/api/v1/water-levels" in doc
        assert "07-workflow-hydrosim-handoff.html" in doc
        assert "format=csv" in doc or '"format"' in doc


class TestSystem7RatingPhysicsDocumentation:
    """Validate System 7 (Rating Physics & Monotone PCHIP Spline)."""

    def test_rating_physics_and_stage_converter_symbols(self) -> None:
        import src.hydrology.rating_physics as physics
        import src.hydrology.stage_converter as sc

        assert hasattr(physics, "wetted_properties"), "wetted_properties missing from rating_physics.py"
        assert hasattr(physics, "station_from_points"), "station_from_points missing from rating_physics.py"

        for fn in [
            "build_calibrated_rating_curve",
            "get_shivaji_rating_curve",
            "get_rajaram_rating_curve",
            "convert_stage_to_discharge_manning",
            "convert_discharge_to_stage_manning",
            "stage_to_discharge",
            "discharge_to_stage",
        ]:
            assert hasattr(sc, fn), f"Function {fn} missing from stage_converter.py"

    def test_rating_docs_match_physical_anchors(self) -> None:
        doc = (DOCS_DIR / "stage-discharge-conversion.md").read_text(encoding="utf-8")
        assert "528.670" in doc  # Shivaji bed RL
        assert "529.318" in doc  # Rajaram bed RL
        assert "PCHIP" in doc
        assert "convert_stage_to_discharge_manning" in doc
        assert "convert_discharge_to_stage_manning" in doc


class TestSystem8TestSuiteDocumentation:
    """Validate System 8 (Comprehensive Test Architecture Inventory)."""

    def test_all_documented_test_files_exist_on_disk(self) -> None:
        doc = (DOCS_DIR / "deployment-operations.md").read_text(encoding="utf-8")
        documented_test_files = re.findall(r"`(tests/test_[a-zA-Z0-9_\-]+\.py)`", doc)
        assert len(documented_test_files) >= 20, f"Expected at least 20 test modules documented, found {len(documented_test_files)}"

        for tf in set(documented_test_files):
            test_path = REPO_ROOT / tf
            assert test_path.is_file(), f"Documented test file {tf} does not physically exist at {test_path}"

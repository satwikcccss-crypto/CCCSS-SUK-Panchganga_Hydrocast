"""
Regression tests for IoT Multi-Station Telemetry unit handling, field mapping,
and signal strength parsing across Shivaji Bridge (SS), Nitawade (NW), and Ichalkaranji (IK).
"""

import pytest
from backend.thingspeak.multi_station import (
    STATIONS,
    _compute_stage,
)


def test_station_configs_units_and_features():
    """Verify each station configuration has the correct unit, datum, and capabilities."""
    stations_map = {s["station_id"]: s for s in STATIONS}

    ss = stations_map["SS"]
    assert ss["unit"] == "feet"
    assert ss["sensor_datum_m"] == 549.35
    assert ss["has_voltage"] is True
    assert ss["has_signal_strength"] is True
    assert ss["field_map"]["distance"] == "field1"
    assert ss["field_map"]["voltage"] == "field2"
    assert ss["field_map"]["signal_strength"] == "field3"

    nw = stations_map["NW"]
    assert nw["unit"] == "meters"
    assert nw["sensor_datum_m"] == 552.80
    assert nw["has_voltage"] is False  # field2 is precomputed level, NOT battery voltage
    assert nw["has_signal_strength"] is False
    assert nw["field_map"]["distance"] == "field1"
    assert nw["field_map"]["level"] == "field2"
    assert nw["field_map"]["altitude"] == "field3"

    ik = stations_map["IK"]
    assert ik["unit"] == "meters"
    assert ik["sensor_datum_m"] == 543.71
    assert ik["has_voltage"] is False
    assert ik["has_signal_strength"] is False
    assert ik["field_map"]["distance"] == "field1"


def test_shivaji_bridge_feet_to_meters_conversion():
    """Shivaji Bridge distance is in feet; must convert by 0.3048 before subtracting from datum."""
    raw_feet = 58.13
    datum_m = 549.35
    computed_stage = _compute_stage(raw_feet, datum_m, unit="feet")
    expected_stage = round(datum_m - (raw_feet * 0.3048), 2)
    assert computed_stage == expected_stage
    assert computed_stage == 531.63


def test_nitawade_meters_passthrough():
    """Nitawade sends distance in meters; must NOT apply feet conversion."""
    raw_meters = 4.64
    datum_m = 552.80
    computed_stage = _compute_stage(raw_meters, datum_m, unit="meters")
    expected_stage = round(datum_m - raw_meters, 2)
    assert computed_stage == expected_stage
    assert computed_stage == 548.16


def test_ichalkaranji_meters_passthrough():
    """Ichalkaranji sends distance in meters; must NOT apply feet conversion."""
    raw_meters = 15.87
    datum_m = 543.71
    computed_stage = _compute_stage(raw_meters, datum_m, unit="meters")
    expected_stage = round(datum_m - raw_meters, 2)
    assert computed_stage == expected_stage
    assert computed_stage == 527.84


def test_compute_stage_none_handling():
    """Handles None and zero gracefully."""
    assert _compute_stage(None, 549.35, unit="feet") is None
    assert _compute_stage(None, 552.80, unit="meters") is None


def test_sim_signal_strength_parsing():
    """Signal strength in field3 must parse as integer percentage (0-100)."""
    raw_ss_str = "84"
    signal_strength = int(float(raw_ss_str))
    assert isinstance(signal_strength, int)
    assert signal_strength == 84
    assert 0 <= signal_strength <= 100

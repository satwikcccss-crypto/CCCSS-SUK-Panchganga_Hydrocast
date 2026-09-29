"""
src/hms/basin_parser.py
=======================
Loads the authoritative HEC-HMS ``Basin_1.basin`` project file into plain
dicts so the pure-Python emulator (``src/hms/runner.py``) and the adaptive
calibration engine (``src/hydrology/ml_calibration.py``) always reproduce the
exact same subbasin / reach hydrology that HEC-HMS itself executes.

Source of truth:
    The ``.basin`` file is the single canonical parameter store for the
    Panchganga RJKT model.  HEC-HMS cannot run on the production Linux box, so
    the emulator must mirror whatever HEC-HMS would compute from this file.
    Any deviation here silently breaks "carrying the exact same runoff from
    the subbasins to the reaches".
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, Tuple

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASIN_FILE = PROJECT_ROOT / "data" / "hms" / "HMS_Automation_RJKT" / "Basin_1.basin"

SUBBASIN_NAMES: Dict[str, str] = {
    "S1": "Karveer",
    "S2": "Sangarul",
    "S3": "Kotoli",
    "S4": "Karanjphen",
    "S5": "Padasali",
    "S6": "Gaganbawda",
    "S7": "Garivade",
    "S8": "Beed",
    "S9": "Radhanagari",
}

# Official Basin_1.basin values — used only as a fallback when the file is
# missing / unreadable (e.g. a minimal deployment container).
FALLBACK_SUB_MODELS: Dict[str, Dict[str, Any]] = {
    "S1": {"name": "Karveer",     "area_km2": 86.213, "cn": 74.848945, "lag_min": 2151.961246},
    "S2": {"name": "Sangarul",    "area_km2": 153.77, "cn": 65.7438039, "lag_min": 3154.252682},
    "S3": {"name": "Kotoli",      "area_km2": 261.32, "cn": 64.8169278, "lag_min": 3997.700714},
    "S4": {"name": "Karanjphen",  "area_km2": 262.00, "cn": 61.8906009, "lag_min": 3115.505941},
    "S5": {"name": "Padasali",    "area_km2": 106.39, "cn": 60.967329,  "lag_min": 2117.085349},
    "S6": {"name": "Gaganbawda",  "area_km2": 227.72, "cn": 61.7827985, "lag_min": 3318.071262},
    "S7": {"name": "Garivade",    "area_km2": 195.39, "cn": 61.2814615, "lag_min": 3362.265784},
    "S8": {"name": "Beed",        "area_km2": 177.44, "cn": 65.7647998, "lag_min": 3387.149566},
    "S9": {"name": "Radhanagari", "area_km2": 366.97, "cn": 64.3060626, "lag_min": 5199.04366},
}

FALLBACK_REACHES: Dict[str, Dict[str, Any]] = {
    "R5": {"k_hr": 4.619, "x": 0.2},
    "R4": {"k_hr": 1.224, "x": 0.2},
    "R2": {"k_hr": 11.827, "x": 0.2},
    "R3": {"k_hr": 3.829, "x": 0.2},
    "R1": {"k_hr": 2.899, "x": 0.2},
}

_FLOAT = r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?"


def _element_blocks(text: str):
    """Yield (kind, name, block_text) for each top-level HEC-HMS element."""
    header_re = re.compile(r"(?m)^(Subbasin|Reach|Sink):\s+(\S+)\s*$")
    end_re = re.compile(r"(?m)^End:\s*$")
    for m in header_re.finditer(text):
        body_end = end_re.search(text, m.end())
        if body_end is None:
            continue
        yield m.group(1), m.group(2), text[m.end():body_end.start()]


def parse_basin_file(path: Path = BASIN_FILE) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """
    Parse ``Basin_1.basin`` into ``(sub_models, reaches)``.

    Subbasin dict entries:
        {"name": str, "area_km2": float, "cn": float, "lag_min": float}
    Reach dict entries:
        {"k_hr": float, "x": float}
    On any failure the official file fallback values are returned.
    """
    if not Path(path).exists():
        log.warning("Basin file %s not found — using built-in official parameters.", path)
        return _deepcopy_fallback()

    try:
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        log.error("Cannot read basin file %s (%s) — using built-in official parameters.", path, exc)
        return _deepcopy_fallback()

    sub_models: Dict[str, Dict[str, Any]] = {}
    reaches: Dict[str, Dict[str, Any]] = {}

    for kind, name, block in _element_blocks(text):
        if kind == "Subbasin":
            area_m = re.search(rf"(?m)^\s*Area:\s*({_FLOAT})", block)
            cn_m = re.search(rf"(?m)^\s*Curve Number:\s*({_FLOAT})", block)
            lag_m = re.search(rf"(?m)^\s*Lag:\s*({_FLOAT})", block)
            if not (area_m and cn_m and lag_m):
                log.warning("Ignoring incomplete subbasin block %s", name)
                continue
            sub_models[name] = {
                "name": SUBBASIN_NAMES.get(name, name),
                "area_km2": float(area_m.group(1)),
                "cn": float(cn_m.group(1)),
                "lag_min": float(lag_m.group(1)),
            }
        elif kind == "Reach":
            k_m = re.search(rf"(?m)^\s*Muskingum K:\s*({_FLOAT})", block)
            x_m = re.search(rf"(?m)^\s*Muskingum x:\s*({_FLOAT})", block)
            if not (k_m and x_m):
                log.warning("Ignoring incomplete reach block %s", name)
                continue
            reaches[name] = {"k_hr": float(k_m.group(1)), "x": float(x_m.group(1))}

    if not sub_models or not reaches:
        log.warning("Basin file %s yielded no usable elements — using built-in official parameters.", path)
        return _deepcopy_fallback()

    log.info(
        "Loaded Basin_1.basin: %d subbasins, %d reaches "
        "(R=%s, X=%s)",
        len(sub_models), len(reaches),
        {r: reaches[r]["k_hr"] for r in sorted(reaches)},
        {r: reaches[r]["x"] for r in sorted(reaches)},
    )
    return sub_models, reaches


def load_basin_parameters() -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Public helper: authoritative subbasin + reach parameters."""
    return parse_basin_file()


def _deepcopy_fallback():
    import copy
    return copy.deepcopy(FALLBACK_SUB_MODELS), copy.deepcopy(FALLBACK_REACHES)


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    subs, reaches = load_basin_parameters()
    print(json.dumps({"subbasins": subs, "reaches": reaches}, indent=2))
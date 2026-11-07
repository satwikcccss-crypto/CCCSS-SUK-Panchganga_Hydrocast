"""
backend/alerts/evaluator.py
============================
CWC / WRD flood threshold evaluation for the Panchganga catchment.

Evaluates forecast bridge stages against Central Water Commission (CWC)
alert classifications: NORMAL / ALERT / WARNING / DANGER / HISTORIC PEAK.

Strictly light-theme friendly — pure business logic, no UI dependencies.
"""

import logging
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)

# CWC alert thresholds (m MSL) — Shivaji Bridge & Rajaram Weir
# From database/seeds.sql bridge_sites seed data
CWC_THRESHOLDS: Dict[str, Dict[str, float]] = {
    "SHIVAJI_BRIDGE": {
        "alert": 542.10,
        "warning": 542.70,
        "danger": 543.30,
        "hfl": 545.33,
    },
    "RAJARAM_WEIR": {
        "alert": 541.50,
        "warning": 542.07,
        "danger": 543.30,
        "hfl": 545.33,
    },
    # Legacy alias used by some tests and older code paths
    "RAJARAM_BRIDGE": {
        "alert": 541.50,
        "warning": 542.07,
        "danger": 543.30,
        "hfl": 545.33,
    },
}


def classify_stage(site_id: str, stage_m: float) -> str:
    """
    Classify a single stage reading against CWC thresholds.

    Returns one of: NORMAL, ALERT, WARNING, DANGER, HISTORIC_PEAK
    """
    thresholds = CWC_THRESHOLDS.get(site_id)
    if thresholds is None:
        log.warning("No CWC thresholds defined for site %s — defaulting to NORMAL", site_id)
        return "NORMAL"

    if stage_m >= thresholds["hfl"]:
        return "HISTORIC_PEAK"
    if stage_m >= thresholds["danger"]:
        return "DANGER"
    if stage_m >= thresholds["warning"]:
        return "WARNING"
    if stage_m >= thresholds["alert"]:
        return "ALERT"
    return "NORMAL"


def evaluate_alerts(bridge_stages: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Evaluate forecast bridge stages against CWC / WRD flood thresholds.

    Parameters
    ----------
    bridge_stages : dict, optional
        Mapping of site_id -> {peak_stage_m, warning_level, danger_level, ...}
        as produced by Step 09 (stage_conversion).

    Returns
    -------
    dict
        {
            "status": "normal" | "alert" | "warning" | "danger" | "historic_peak",
            "alerts_issued": int,
            "sites": { site_id: {"stage": float, "classification": str, ...} }
        }
    """
    if not bridge_stages:
        return {"alerts_issued": 0, "status": "normal", "sites": {}}

    sites: Dict[str, Any] = {}
    max_severity = "NORMAL"
    severity_order = ["NORMAL", "ALERT", "WARNING", "DANGER", "HISTORIC_PEAK"]
    alerts_issued = 0

    for site_id, data in bridge_stages.items():
        stage_m = float(data.get("peak_stage_m", 0.0)) if data else 0.0
        classification = classify_stage(site_id, stage_m)

        sites[site_id] = {
            "stage_m": round(stage_m, 2),
            "classification": classification,
            "thresholds": CWC_THRESHOLDS.get(site_id, {}),
        }

        if classification != "NORMAL":
            alerts_issued += 1

        if severity_order.index(classification) > severity_order.index(max_severity):
            max_severity = classification

    status = max_severity.lower()

    log.info(
        "CWC alert evaluation: %d alerts issued, max status=%s",
        alerts_issued, status,
    )

    return {
        "alerts_issued": alerts_issued,
        "status": status,
        "sites": sites,
    }


def _get_bridge_metadata(conn: Any, site_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch bridge metadata from the database for a given site.

    Falls back to the CWC_THRESHOLDS constants when the database row is
    unavailable (e.g. in tests with a mocked connection).

    Parameters
    ----------
    conn : Any
        Active database connection.
    site_id : str
        Bridge site identifier (e.g. "SHIVAJI_BRIDGE").

    Returns
    -------
    dict or None
        Bridge metadata row, or None if not found and no fallback exists.
    """
    thresholds = CWC_THRESHOLDS.get(site_id)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT site_id, site_name, alert_stage_m, warning_stage_m,
                       danger_stage_m, hfl_m, zero_datum_m, sensor_datum_m
                FROM bridge_sites WHERE site_id = %s
                """,
                (site_id,),
            )
            row = cur.fetchone()
            if row is not None and thresholds is not None:
                return {
                    "site_id": row[0],
                    "site_name": row[1],
                    "alert": float(row[2]),
                    "warning": float(row[3]),
                    "danger": float(row[4]),
                    "hfl": float(row[5]),
                    "zero_datum_m": float(row[6]),
                    "sensor_datum_m": float(row[7]),
                }
    except Exception as exc:
        log.warning("Could not fetch bridge metadata for %s: %s", site_id, exc)

    # Fallback to CWC_THRESHOLDS constants when DB row unavailable
    if thresholds is not None:
        return {
            "site_id": site_id,
            "site_name": site_id,
            "alert": thresholds["alert"],
            "warning": thresholds["warning"],
            "danger": thresholds["danger"],
            "hfl": thresholds["hfl"],
        }
    return None


def evaluate_and_notify(
    bridge_stages: Dict[str, Any],
    conn: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Evaluate bridge stages and optionally persist alerts to the database.

    Parameters
    ----------
    bridge_stages : dict
        Mapping of site_id -> stage data.
    conn : Any, optional
        Active database connection for persistence.

    Returns
    -------
    dict
        Evaluation result with alerts_issued, status, and sites.
    """
    result = evaluate_alerts(bridge_stages)

    if conn is not None and result["alerts_issued"] > 0:
        try:
            with conn.cursor() as cur:
                for site_id, site_data in result["sites"].items():
                    cur.execute(
                        """
                        INSERT INTO alert_events
                            (site_id, classification, stage_m, created_at)
                        VALUES (%s, %s, %s, NOW())
                        ON CONFLICT DO NOTHING
                        """,
                        (
                            site_id,
                            site_data["classification"],
                            site_data["stage_m"],
                        ),
                    )
                conn.commit()
        except Exception as exc:
            log.warning("Could not persist alert events: %s", exc)

    return result


__all__ = ["evaluate_alerts", "classify_stage", "CWC_THRESHOLDS",
           "_get_bridge_metadata", "evaluate_and_notify"]

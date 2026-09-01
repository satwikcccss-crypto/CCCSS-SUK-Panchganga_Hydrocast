"""
Dynamic Subbasin Station Selector & Spatial Fallback Engine
============================================================
Dynamically evaluates rainfall volume across Primary & Alternate stations for each
Panchganga subbasin (S1 to S9).
Selects the maximum-rainfall station for conservative flood forecasting in HEC-HMS.
For ungauged subbasins, performs spatial nearest-neighbor assignment to the closest
high-rainfall station.
"""

import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

log = logging.getLogger(__name__)


@dataclass
class RainStation:
    station_id: str
    name: str
    subbasin: str
    lon: float
    lat: float
    is_primary: bool = True
    elevation_m: float = 600.0


# ── Full Primary & Alternate Station Registry ─────────────────────────────────

STATION_REGISTRY: List[RainStation] = [
    # S1
    RainStation("KARVIR", "Karvir", "S1", 74.2481772, 16.706369, is_primary=True, elevation_m=550.0),
    
    # S2
    RainStation("SANGARUL", "Sangarul", "S2", 74.0931627, 16.6841962, is_primary=True, elevation_m=572.0),
    RainStation("BALINGA", "Balinga", "S2", 74.17031, 16.6878443, is_primary=False, elevation_m=560.0),
    RainStation("KALE", "Kale", "S2", 74.0564499, 16.7228087, is_primary=False, elevation_m=580.0),
    
    # S3
    RainStation("KOTOLI", "Kotoli", "S3", 74.0518705, 16.7820174, is_primary=True, elevation_m=585.0),
    RainStation("BAJAR_BHOGAON", "Bajar Bhogaon", "S3", 74.1107824, 16.8086769, is_primary=False, elevation_m=590.0),
    RainStation("PADAL", "Padal", "S3", 74.115187, 16.7446006, is_primary=False, elevation_m=575.0),
    
    # S4
    RainStation("BEED", "Beed", "S4", 74.1288964, 16.647984, is_primary=True, elevation_m=565.0),
    
    # S5
    RainStation("SALWAN", "Salwan", "S5", 73.9735, 16.6712, is_primary=True, elevation_m=595.0),
    
    # S6
    RainStation("KARANJPHEN", "Karanjphen", "S6", 73.9036487, 16.7850973, is_primary=True, elevation_m=640.0),
    RainStation("GAGANBAWDA", "Gaganbawda", "S6", 73.8346738, 16.5469926, is_primary=False, elevation_m=680.0),
    
    # S7
    RainStation("RADHANAGARI", "Radhanagari", "S7", 73.9971822, 16.41021, is_primary=True, elevation_m=615.0),
    
    # S8
    RainStation("SHIROLI_DHUMALA", "Shiroli-Dhumala", "S8", 74.1062828, 16.6166768, is_primary=False, elevation_m=560.0),
    
    # S9
    RainStation("HALADI", "Haladi", "S9", 74.156292, 16.5932632, is_primary=False, elevation_m=555.0),
    RainStation("RASHIWADE_BK", "Rashiwade Bk.", "S9", 74.1019728, 16.5475641, is_primary=False, elevation_m=570.0),
    RainStation("AAVALI_BK", "Aavali Bk.", "S9", 74.0549812, 16.481009, is_primary=False, elevation_m=585.0),
    RainStation("KASABA_TARALE", "Kasaba Tarale", "S9", 74.021589, 16.4478876, is_primary=False, elevation_m=595.0),
    RainStation("KASABA_WALAWE", "Kasaba Walawe", "S9", 73.9971822, 16.41021, is_primary=False, elevation_m=615.0),
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Great-Circle distance in km between two lat/lon coordinates."""
    r = 6371.0  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    return 2.0 * r * math.asin(math.sqrt(a))


def select_active_subbasin_gages(
    station_rainfall_90hr: Dict[str, float]
) -> Dict[str, dict]:
    """
    Selects the governing rainfall gage for each subbasin (S1–S9).
    
    Parameters:
        station_rainfall_90hr: Dict[station_id, total_cumulative_mm]
        
    Returns:
        Dict[subbasin_id, {
            'selected_station_id': str,
            'station_name': str,
            'cumulative_mm': float,
            'method': 'MAX_RAIN_VOLUME' | 'NEAREST_HIGH_RAIN_FALLBACK',
            'candidates_count': int
        }]
    """
    # Group stations by subbasin
    by_subbasin: Dict[str, List[RainStation]] = {}
    for st in STATION_REGISTRY:
        by_subbasin.setdefault(st.subbasin, []).append(st)

    all_subbasins = [f"S{i}" for i in range(1, 10)]
    selection_results = {}

    for sub_id in all_subbasins:
        candidates = by_subbasin.get(sub_id, [])

        if candidates:
            # Sort candidates by rainfall volume descending
            scored = []
            for c in candidates:
                rf = station_rainfall_90hr.get(c.station_id, 0.0)
                scored.append((rf, c))
            
            scored.sort(key=lambda x: x[0], reverse=True)
            best_rf, best_st = scored[0]

            selection_results[sub_id] = {
                "subbasin_id": sub_id,
                "selected_station_id": best_st.station_id,
                "station_name": best_st.name,
                "lat": best_st.lat,
                "lon": best_st.lon,
                "cumulative_mm": round(best_rf, 2),
                "method": "MAX_RAIN_VOLUME",
                "candidates_count": len(candidates),
                "alternate_stations": [s[1].name for s in scored[1:]],
            }
        else:
            # Ungauged subbasin fallback: Find nearest high-rainfall station
            # Subbasin approximate centroids
            sub_centroids = {
                "S1": (16.706, 74.248),
                "S2": (16.684, 74.093),
                "S3": (16.782, 74.051),
                "S4": (16.648, 74.128),
                "S5": (16.671, 73.973),
                "S6": (16.785, 73.903),
                "S7": (16.410, 73.997),
                "S8": (16.616, 74.106),
                "S9": (16.547, 74.101),
            }
            c_lat, c_lon = sub_centroids.get(sub_id, (16.65, 74.10))

            # Rank all stations by distance and rainfall
            fallback_scored = []
            for st in STATION_REGISTRY:
                dist = haversine_km(c_lat, c_lon, st.lat, st.lon)
                rf = station_rainfall_90hr.get(st.station_id, 0.0)
                # Score: maximize rainfall while penalizing distant stations
                score = rf / (dist + 1.0)
                fallback_scored.append((score, dist, rf, st))

            fallback_scored.sort(key=lambda x: x[0], reverse=True)
            _, best_dist, best_rf, best_st = fallback_scored[0]

            selection_results[sub_id] = {
                "subbasin_id": sub_id,
                "selected_station_id": best_st.station_id,
                "station_name": best_st.name,
                "lat": best_st.lat,
                "lon": best_st.lon,
                "cumulative_mm": round(best_rf, 2),
                "method": "NEAREST_HIGH_RAIN_FALLBACK",
                "candidates_count": 0,
                "fallback_distance_km": round(best_dist, 1),
            }

    return selection_results

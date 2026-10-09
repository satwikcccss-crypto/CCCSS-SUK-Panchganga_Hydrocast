"""Lock the embedded cross-sections to the official WRD ground survey.

The two gauging sites are described by full surveyed cross-sections:

  * Shivaji Bridge  -- X-Section 17, chainage 6+257 m, bed RL 528.670 m MSL
  * Rajaram K.T. Weir -- X-Section 29, chainage 10+115 m, bed RL 529.318 m MSL

``src/hydrology/stage_converter.py`` embeds both coordinate lists so the model
has no runtime file dependency. These tests pin that embedded geometry to the
authoritative survey copies in ``data/wrd_cross_sections/``, so an edit to the
embedded arrays cannot silently drift away from the surveyed section.

They also pin the baseflow behaviour that follows from the survey:

  * discharge is exactly 0 at the surveyed bed level,
  * discharge rises monotonically as the wetted area and perimeter grow,
  * the surveyed wetted geometry alone over-predicts the government-gauged
    discharge, which is why discharge comes from the WRD PCHIP anchors while
    the survey supplies the wetted area and perimeter.
"""

import re
from pathlib import Path

import numpy as np
import pytest

from src.hydrology import stage_converter as sc

SURVEY_DIR = Path(__file__).resolve().parents[1] / "data" / "wrd_cross_sections"

_POINT_RE = re.compile(r"\[\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\]")

# name, embedded array, survey file, bed RL, point count, section width (m)
SITES = [
    (
        "SHIVAJI_BRIDGE",
        "SHIVAJI_SURVEY",
        "shivaji_xsection_17_survey.txt",
        528.670,
        146,
        404.4,
    ),
    (
        "RAJARAM_WEIR",
        "RAJARAM_SURVEY",
        "rajaram_xsection_29_survey.txt",
        529.318,
        193,
        461.1,
    ),
]


def _load_survey(filename: str) -> np.ndarray:
    text = (SURVEY_DIR / filename).read_text(encoding="utf-8")
    pts = [[float(g) for g in m] for m in _POINT_RE.findall(text)]
    assert pts, f"no survey points parsed from {filename}"
    return np.array(pts, dtype=np.float64)


@pytest.mark.parametrize(
    "site,attr,filename,bed_rl,n_pts,width_m", SITES,
    ids=[s[0] for s in SITES],
)
class TestSurveyedCrossSections:
    def test_bed_level_matches_survey(self, site, attr, filename, bed_rl, n_pts, width_m):
        assert getattr(sc, attr)[:, 2].min() == pytest.approx(bed_rl, abs=1e-9)

    def test_point_count_matches_survey(self, site, attr, filename, bed_rl, n_pts, width_m):
        assert len(getattr(sc, attr)) == n_pts

    def test_embedded_geometry_is_identical_to_survey(
        self, site, attr, filename, bed_rl, n_pts, width_m
    ):
        embedded = getattr(sc, attr)
        survey = _load_survey(filename)
        assert embedded.shape == survey.shape
        # Exact equality, not a tolerance: these are transcribed coordinates.
        assert np.array_equal(embedded, survey), (
            f"{attr} has drifted from {filename}"
        )

    def test_bed_constant_matches_geometry(self, site, attr, filename, bed_rl, n_pts, width_m):
        if site == "SHIVAJI_BRIDGE":
            assert sc.SHIVAJI_BED_RL_M == pytest.approx(bed_rl, abs=1e-9)
        else:
            assert sc.RAJARAM_BED_RL_M == pytest.approx(bed_rl, abs=1e-9)

    def test_section_width_from_survey(self, site, attr, filename, bed_rl, n_pts, width_m):
        pts = getattr(sc, attr)
        dx = np.diff(pts[:, 1])
        dy = np.diff(pts[:, 0])
        total = float(np.sum(np.hypot(dx, dy)))
        assert total == pytest.approx(width_m, rel=0.02)

    def test_discharge_is_zero_at_surveyed_bed(
        self, site, attr, filename, bed_rl, n_pts, width_m
    ):
        q = sc.convert_stage_to_discharge_manning(bed_rl, site)
        assert q == pytest.approx(0.0, abs=1e-9)

    def test_wetted_properties_zero_at_bed_and_grow_with_stage(
        self, site, attr, filename, bed_rl, n_pts, width_m
    ):
        pts = getattr(sc, attr)
        northings, eastings, elevs = pts[:, 0], pts[:, 1], pts[:, 2]
        station = np.concatenate(
            [[0.0], np.cumsum(np.hypot(np.diff(eastings), np.diff(northings)))]
        )

        areas, perimeters, flows = [], [], []
        for wse in np.linspace(bed_rl, bed_rl + 3.0, 25):
            a, p = sc._wetted_properties(station, elevs, float(wse))
            areas.append(a)
            perimeters.append(p)
            flows.append(sc.convert_stage_to_discharge_manning(float(wse), site))

        # Zero level -> no wetted area, no wetted perimeter, no discharge.
        assert areas[0] == pytest.approx(0.0, abs=1e-9)
        assert perimeters[0] == pytest.approx(0.0, abs=1e-9)
        assert flows[0] == pytest.approx(0.0, abs=1e-9)

        # Wetted perimeter and discharge grow monotonically as the level rises.
        assert all(x <= y + 1e-9 for x, y in zip(perimeters, perimeters[1:]))
        assert all(x <= y + 1e-9 for x, y in zip(areas, areas[1:]))
        assert all(x <= y + 1e-9 for x, y in zip(flows, flows[1:]))
        assert flows[-1] > flows[0]

    def test_forty_cubic_metres_is_a_level_not_a_floor(
        self, site, attr, filename, bed_rl, n_pts, width_m
    ):
        # 40 m3/s is a legitimate baseflow, but only at its own stage. It must
        # never be imposed at every level.
        stage_for_40 = sc.convert_discharge_to_stage_manning(40.0, site)
        assert stage_for_40 > bed_rl + 2.0, "40 m3/s should not sit near the bed"
        assert sc.convert_stage_to_discharge_manning(stage_for_40, site) == pytest.approx(
            40.0, rel=0.02
        )
        # Well below that stage the discharge must be far under 40.
        assert sc.convert_stage_to_discharge_manning(bed_rl + 1.0, site) < 40.0


class TestSurveyGeometryCannotSetTheMagnitude:
    """Why discharge comes from WRD anchors and not from Manning on the survey."""

    def test_manning_on_survey_overpredicts_wrd_gauged_discharge(self):
        pts = sc.SHIVAJI_SURVEY
        northings, eastings, elevs = pts[:, 0], pts[:, 1], pts[:, 2]
        station = np.concatenate(
            [[0.0], np.cumsum(np.hypot(np.diff(eastings), np.diff(northings)))]
        )

        wse = 533.54  # WRD sheet: 80.00 m3/s
        area, perim = sc._wetted_properties(station, elevs, wse)
        radius = area / perim
        slope, n_main = 0.00021547, 0.031
        q_manning = (1.0 / n_main) * area * radius ** (2.0 / 3.0) * np.sqrt(slope)

        assert area == pytest.approx(228.4, rel=0.02)
        assert perim == pytest.approx(84.2, rel=0.02)
        # Manning on the surveyed section returns ~210 m3/s against WRD's 80.
        assert q_manning == pytest.approx(210.0, rel=0.05)
        assert q_manning > 2.0 * 80.0
        # The authoritative curve is the WRD-gauged one.
        assert sc.convert_stage_to_discharge_manning(wse, "SHIVAJI_BRIDGE") < q_manning
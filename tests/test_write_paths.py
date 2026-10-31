"""
tests/test_write_paths.py
=========================
Coverage for the three persistence / output modules that were previously at 0%:

  * ``src.dss.writer``          — HEC-DSS hyetograph writer (pydsstools optional)
  * ``src.db.store_results``    — hydrograph / peak / runoff persistence
  * ``src.hydrology.post_process`` — Q→H bridge forecasts + DB persistence

No database and no pydsstools are required: connection and DSS objects are
lightweight doubles, so these tests run identically on any machine/CI.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.db import store_results
from src.dss import writer
from src.hydrology import post_process as pp


# ─────────────────────────── shared DB doubles ─────────────────────────────

class _Cursor:
    def __init__(self, sink):
        self._sink = sink
        self._rows = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        flat = " ".join(sql.split())
        if params is not None:
            n_placeholders = flat.count("%s")
            assert n_placeholders == len(params), (
                f"SQL placeholder/param mismatch: {n_placeholders} placeholders "
                f"vs {len(params)} params :: {flat}"
            )
        self._sink.append((flat, params))

    def fetchall(self):
        return self._rows


class _Conn:
    def __init__(self):
        self.sql = []
        self.commits = 0

    def cursor(self, **kwargs):
        return _Cursor(self.sql)

    def commit(self):
        self.commits += 1


def _utc(hour=6):
    return datetime(2026, 8, 22, hour, tzinfo=timezone.utc)


# ═════════════════════════════ src.dss.writer ══════════════════════════════

def test_hec_dtime_format():
    assert writer._hec_dtime(datetime(2026, 1, 5, 6, 0, 0)) == "05JAN2026 06:00:00"


def test_gage_mapping_shared_gauge():
    # Met_1.met: Salwan is shared by S5/S6/S7.
    assert writer.GAGE_SUBBASINS["Salwan"] == ["S5", "S6", "S7"]
    assert writer.SUBBASIN_TO_GAGE["S9"] == "Radhanagari"


def test_write_gage_to_dss_pathname_and_container(monkeypatch):
    class _TSC:
        pass

    monkeypatch.setattr(writer, "TimeSeriesContainer", _TSC)

    put = []

    class _DSS:
        def put(self, tsc):
            put.append(tsc)

    pn = writer.write_gage_to_dss(_DSS(), "Karvir", [1.0, 2.0, 3.0], _utc())

    assert pn == "//Karvir/PRECIP-INC/22AUG2026/1HOUR/GAGE/"
    tsc = put[0]
    assert tsc.values == [1.0, 2.0, 3.0]
    assert tsc.units == "MM"
    assert tsc.type == "INST-VAL"
    assert tsc.numberValues == 3


def test_write_all_subbasins_requires_pydsstools(monkeypatch):
    monkeypatch.setattr(writer, "HecDss", None)
    with pytest.raises(RuntimeError):
        writer.write_all_subbasins({}, _utc())


def test_write_all_subbasins_aggregates_shared_gauge(monkeypatch):
    class _Open:
        def __init__(self, *_a, **_k):
            pass

        def __enter__(self):
            return object()

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(writer, "HecDss", SimpleNamespace(Open=_Open))

    captured = []

    def _fake_write(dss, gage, vals, run_time):
        captured.append((gage, vals))
        return f"//{gage}/"

    monkeypatch.setattr(writer, "write_gage_to_dss", _fake_write)

    results = {
        "S1": SimpleNamespace(hyetograph=[5.0, 6.0]),
        "S5": SimpleNamespace(hyetograph=[1.0, 2.0]),
        "S6": SimpleNamespace(hyetograph=[3.0, 4.0]),
        "S99": SimpleNamespace(hyetograph=[9.0]),  # unmapped -> skipped
    }
    written = writer.write_all_subbasins(results, _utc())

    by_gage = dict(captured)
    assert set(by_gage) == {"Karvir", "Salwan"}      # S99 skipped
    assert by_gage["Salwan"] == [2.0, 3.0]           # mean of S5/S6
    assert by_gage["Karvir"] == [5.0, 6.0]
    assert len(written) == 2


def _fake_dss(gage_paths, read_values):
    class _Open:
        def __init__(self, *_a, **_k):
            pass

        def __enter__(self):
            return SimpleNamespace(
                getPathnameList=lambda pattern: gage_paths,
                read=lambda pn: SimpleNamespace(values=read_values),
            )

        def __exit__(self, *exc):
            return False

    return SimpleNamespace(Open=_Open)


def test_verify_dss_ok_when_readback_has_rain(monkeypatch):
    monkeypatch.setattr(writer, "HecDss", _fake_dss(["pn1"], [1.0, 2.0, -9999.0]))
    assert writer.verify_dss(writer.DSS_FILE, ["S1", "S9"]) is True


def test_verify_dss_fails_when_record_missing(monkeypatch):
    monkeypatch.setattr(writer, "HecDss", _fake_dss([], []))
    assert writer.verify_dss(writer.DSS_FILE, ["S1"]) is False


def test_verify_dss_false_without_pydsstools(monkeypatch):
    monkeypatch.setattr(writer, "HecDss", None)
    assert writer.verify_dss(writer.DSS_FILE, ["S1"]) is False


# ═══════════════════════ src.db.store_results ═════════════════════════════

def _hydrograph(peaks=(120.0, 950.0, 400.0), base=_utc()):
    rows = [(base + timedelta(hours=i), q) for i, q in enumerate(peaks)]
    peak_q = max(peaks)
    peak_ts = next(ts for ts, q in rows if q == peak_q)
    return {
        "hydrograph": rows,
        "peak_q": peak_q,
        "time_of_peak": peak_ts,
        "total_volume_m3": 1_234_567.0,
    }


def test_store_all_writes_three_tables_and_commits():
    conn = _Conn()
    counts = store_results.store_all(
        conn, "CYC_T", _utc(), _hydrograph(), {"SHIVAJI_BRIDGE": {}},
    )

    assert counts == {"hydrograph_rows": 3, "peak_events": 1, "summary_rows": 1}
    assert conn.commits == 1
    sql = " ".join(s for s, _ in conn.sql)
    assert "DELETE FROM hydrograph_results" in sql
    assert "INSERT INTO hydrograph_results" in sql
    assert "INSERT INTO peak_discharge_events" in sql
    assert "INSERT INTO runoff_summary" in sql


def test_store_hydrograph_surface_runoff_uses_hardcoded_baseflow():
    # Documents current behaviour (baseflow = 45.0 hardcode in _store_hydrograph).
    conn = _Conn()
    store_results._store_hydrograph(conn, "CYC_T", _hydrograph(peaks=(45.0, 145.0)))
    inserts = [p for s, p in conn.sql if s.startswith("INSERT INTO hydrograph_results")]
    # params: (cycle_id, ts, lead, q, surf, baseflow, is_peak)
    assert inserts[0][4] == 0.0        # 45 - 45 -> 0
    assert inserts[1][4] == 100.0      # 145 - 45


@pytest.mark.parametrize(
    "peaks, expected",
    [
        ((100.0, 200.0), "normal"),
        ((600.0, 200.0), "watch"),
        ((800.0, 200.0), "warning"),
        ((1100.0, 200.0), "emergency"),
    ],
)
def test_runoff_summary_alert_classification(peaks, expected):
    conn = _Conn()
    store_results._store_runoff_summary(
        conn, "CYC_T", _utc(), _hydrograph(peaks=peaks), {},
    )
    params = conn.sql[0][1]
    assert params[6] == expected


def test_peak_event_uses_lead_hours_to_peak():
    conn = _Conn()
    hg = _hydrograph(peaks=(100.0, 200.0, 50.0))
    store_results._store_peak_event(conn, "CYC_T", _utc(), hg)
    params = conn.sql[0][1]
    assert params[3] == 2  # peak at index 1 -> lead 2


# ═══════════════════════ src.hydrology.post_process ════════════════════════

def _curve():
    return {
        "meta": {
            "alert_stage_m": 534.0,
            "warning_stage_m": 535.0,
            "danger_stage_m": 536.0,
            "hfl_m": 537.0,
        },
        "stage": np.array([528.0, 530.0, 534.0, 536.0, 538.0]),
        "discharge": np.array([0.0, 100.0, 1000.0, 2000.0, 3000.0]),
    }


def test_q_to_h_interpolates_and_clamps():
    curve = _curve()
    assert pp.q_to_h(1500.0, curve) == pytest.approx(535.0)
    assert pp.q_to_h(-5.0, curve) == 528.0       # left clamp
    assert pp.q_to_h(99_999.0, curve) == 538.0   # right clamp


def test_cwc_level_thresholds():
    meta = _curve()["meta"]
    assert pp.cwc_level(538.0, meta) == "HFL_EXCEEDED"
    assert pp.cwc_level(536.0, meta) == "DANGER"
    assert pp.cwc_level(535.0, meta) == "WARNING"
    assert pp.cwc_level(534.0, meta) == "ALERT"
    assert pp.cwc_level(533.9, meta) == "NORMAL"


def test_apply_travel_time_shifts_timestamps_only():
    base = _utc()
    out = pp.apply_travel_time([(base, 10.0), (base + timedelta(hours=1), 20.0)], 1.5)
    assert out[0][0] == base + timedelta(hours=1.5)
    assert [q for _, q in out] == [10.0, 20.0]


def test_convert_and_store_stages_computes_peak_and_arrival(monkeypatch):
    conn = _Conn()
    monkeypatch.setattr(pp, "load_rating_curves_from_db", lambda _c: {"SHIVAJI_BRIDGE": _curve()})

    hg = {
        "hydrograph": [
            (_utc(), 100.0),                      # NORMAL (h=530)
            (_utc() + timedelta(hours=1), 1500.0),  # WARNING (h=535)
            (_utc() + timedelta(hours=2), 500.0),   # ALERT (h<=534)
        ]
    }
    out = pp.convert_and_store_stages(conn, hg, "CYC_T", _utc())

    site = out["SHIVAJI_BRIDGE"]
    assert site["peak_stage"] == pytest.approx(535.0)
    assert site["peak_level"] == "WARNING"
    # arrival = first non-NORMAL row shifted by SHIVAJI travel time 1.5 h
    assert site["arrival_time"] == _utc() + timedelta(hours=2.5)
    assert len(site["forecast"]) == 3
    assert conn.commits == 1
    assert any(s.startswith("INSERT INTO bridge_stage_forecast") for s, _ in conn.sql)


class _QueuedCursor(_Cursor):
    """Cursor whose ``fetchall`` returns a queue of pre-canned result sets."""

    def __init__(self, sink, result_sets):
        super().__init__(sink)
        self._result_sets = list(result_sets)
        self._current = []

    def execute(self, sql, params=None):
        super().execute(sql, params)
        self._current = self._result_sets.pop(0) if self._result_sets else []

    def fetchall(self):
        return self._current


class _QueuedConn(_Conn):
    def __init__(self, result_sets):
        super().__init__()
        self._result_sets = result_sets

    def cursor(self, **kwargs):
        return _QueuedCursor(self.sql, self._result_sets)


def test_load_rating_curves_from_db_builds_arrays():
    sites = [
        {"site_id": "SHIVAJI_BRIDGE", "alert_stage_m": 534.0, "warning_stage_m": 535.0,
         "danger_stage_m": 536.0, "hfl_m": 537.0},
    ]
    rows = [{"stage_m": 528.0, "discharge_m3s": 0.0},
            {"stage_m": 536.0, "discharge_m3s": 2000.0}]
    conn = _QueuedConn([sites, rows])

    curves = pp.load_rating_curves_from_db(conn)

    assert set(curves) == {"SHIVAJI_BRIDGE"}
    assert list(curves["SHIVAJI_BRIDGE"]["stage"]) == [528.0, 536.0]
    assert list(curves["SHIVAJI_BRIDGE"]["discharge"]) == [0.0, 2000.0]
    assert curves["SHIVAJI_BRIDGE"]["meta"]["hfl_m"] == 537.0


def test_convert_and_store_falls_back_to_csv_when_db_empty(monkeypatch):
    conn = _Conn()
    monkeypatch.setattr(pp, "load_rating_curves_from_db", lambda _c: {})

    cs = SimpleNamespace(
        alert_stage_m=534.0, warning_stage_m=535.0,
        danger_stage_m=536.0, hfl_m=537.0,
    )
    df = pd.DataFrame({"stage_m": [528.0, 530.0, 536.0], "q_m3s": [0.0, 100.0, 2000.0]})
    monkeypatch.setattr(pp, "build_all_rating_curves", lambda: {"SHIVAJI_BRIDGE": (cs, df)})

    hg = {"hydrograph": [(_utc(), 2000.0)]}
    out = pp.convert_and_store_stages(conn, hg, "CYC_T", _utc())

    assert out["SHIVAJI_BRIDGE"]["peak_stage"] == pytest.approx(536.0)
    assert out["SHIVAJI_BRIDGE"]["peak_level"] == "DANGER"

"""OC-1: a minimum is a record — read from the styles papers and lists use, converted to BJD_TDB, checked for
duplicates and kind conflicts, written for a paper."""

import numpy as np
import pytest

from astrowb.timeseries import minima_table as mt

EXAMPLES = [  # (text, [(time, error, kind, method, filter)])
    ("2455000.1234 0.0004 I CCD", [(2455000.1234, 0.0004, "I", "ccd", "")]),
    ("2 451 234.5678 ± 0.0004  p  CCD  V  Smith", [(2451234.5678, 0.0004, "I", "ccd", "V")]),
    ("51234.5678(3)  s  pe", [(2451234.5678, 0.0003, "II", "pe", "")]),
    (
        "HJD-2400000  Error  Type\n54321.4567  0.0003  II\n54322.1234 0.0002 I",
        [(2454321.4567, 0.0003, "II", "unknown", ""), (2454322.1234, 0.0002, "I", "unknown", "")],
    ),
    ("2453000.1234*  0.0005  sec  vis", [(2453000.1234, 0.0005, "II", "vis", "")]),
    ("1234.5678 0.0004 p", [(2451234.5678, 0.0004, "I", "unknown", "")]),
    ("2458000.11111\t0.00011\tpri\tTESS", [(2458000.11111, 0.00011, "I", "space", "")]),
    ("# a comment line\n2459000.5 pg   # no error given", [(2459000.5, None, "I", "pg", "")]),
    ("2 452 500.4321(12) II DSLR Rc", [(2452500.4321, 0.0012, "II", "dslr", "Rc")]),
    ("2456789.0001, 0.0001, 2, B.R.N.O.", [(2456789.0001, 0.0001, "II", "unknown", "")]),
]


@pytest.mark.parametrize(("text", "expected"), EXAMPLES)
def test_papers_and_lists_read_as_records(text, expected):
    rows = mt.parse_text(text)
    assert len(rows) == len(expected)
    for row, (t, err, kind, method, filt) in zip(rows, expected, strict=True):
        assert row["time_original"] == pytest.approx(t, abs=1e-6)
        assert row["kind"] == kind and row["method"] == method and row["filter"] == filt
        if err is None:
            assert row["error_assumed"] and row["error"] == mt.DEFAULT_ERRORS[method]  # the method's default
        else:
            assert row["error"] == pytest.approx(err, rel=1e-6) and not row["error_assumed"]


def test_hjd_to_bjd_agrees_with_astropy_from_1900_to_2030():
    """Times made forward from UTC by Astropy (HJD_UTC and BJD_TDB of the same instant) and read back from HJD."""
    import astropy.units as u
    from astropy.coordinates import EarthLocation, SkyCoord
    from astropy.time import Time

    star = SkyCoord(31.04 * u.deg, 46.69 * u.deg)
    utc = Time(np.linspace(Time("1900-03-01").jd, Time("2030-11-01").jd, 9), format="jd", scale="utc")
    geocentre = EarthLocation.from_geocentric(0, 0, 0, unit=u.m)
    hjd = (utc + utc.light_travel_time(star, kind="heliocentric", ephemeris="builtin", location=geocentre)).jd
    bjd = (utc.tdb + utc.light_travel_time(star, kind="barycentric", ephemeris="builtin", location=geocentre)).jd
    rows = [mt.record(h, 0.0005, standard="HJD_UTC") for h in hjd]
    assert mt.add_bjd(rows, star) == 0
    got = np.array([r["bjd_tdb"] for r in rows])
    assert np.max(np.abs(got - bjd)) * 86400 < 0.1


def test_an_unknown_hjd_scale_widens_the_error_by_tt_minus_utc():
    import astropy.units as u
    from astropy.coordinates import SkyCoord

    rows = [mt.record(2459000.5, 0.0001)]  # "HJD unknown" by default
    assert mt.add_bjd(rows, SkyCoord(10 * u.deg, 20 * u.deg)) == 1
    assert rows[0]["error"] == pytest.approx(np.hypot(0.0001, 69.184 / 86400), rel=1e-3)  # TT − UTC in 2020
    assert "unknown" in rows[0]["note"]


def test_duplicates_and_kind_conflicts_are_marked():
    t0, p = 2455000.0, 1.0
    rows = [mt.record(t0 + 10, 0.0004), mt.record(t0 + 10.001, 0.0005), mt.record(t0 + 20.5, 0.0004, "I")]
    assert mt.mark_duplicates(rows) == [rows[1]["id"]] and not rows[1]["use"] and rows[0]["use"]
    assert mt.mark_epoch_conflicts(rows, t0, p) == [rows[2]["id"]]  # a primary at phase 0.5


def test_ecsv_round_trip_is_exact_and_latex_lists_the_used_rows(tmp_path):
    rows = mt.parse_text(EXAMPLES[3][0] + "\n2454323.0 0.0002 I", source="IBVS 1234")
    rows[2]["use"] = False
    path = tmp_path / "minima.ecsv"
    mt.write_ecsv(rows, path)
    back = mt.read_ecsv(path)
    assert [r["id"] for r in back] == [r["id"] for r in rows]
    for a, b in zip(rows, back, strict=True):
        for c in mt.COLUMNS:
            assert (a[c] == b[c]) or (isinstance(a[c], float) and np.isnan(a[c]) and np.isnan(b[c])), c
    latex = mt.to_latex(rows, 2454321.4567 - 0.5, 1.0)
    assert latex.count("IBVS 1234") == 2 and "2454321.45670 & 0.00030 & 0.5 &" in latex

"""ARC-15: uneven time series are flagged; the airmass column names its formula (items 5 d and 6)."""

from astrowb import timing
from astrowb.photometry import lcfile


def test_repeat_backwards_and_gap_are_flagged():
    t = [0, 1, 2, 2, 3, 2.5, 4, 5, 20, 21]
    flags = timing.series_flags(t)
    assert flags == {"repeat": [3], "backwards": [5], "gap": [8]}
    assert timing.series_flags([0, 1, 2, 3]) == {"repeat": [], "backwards": [], "gap": []}
    assert timing.series_flags([5.0]) == {"repeat": [], "backwards": [], "gap": []}


def test_airmass_column_names_its_formula(tmp_path):
    from astropy.table import Table

    lc = {"time": [1.0, 2.0], "rel_flux": [1.0, 1.0], "airmass": [1.2, 1.3], "time_scale": "BJD_TDB"}
    path = lcfile.write(lc, tmp_path / "a.lc.ecsv")
    assert "Young (1994" in Table.read(path, format="ascii.ecsv")["airmass"].description

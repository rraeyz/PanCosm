import numpy as np
from astropy.time import Time

from astrowb.ui.oc_years import year_axis, year_ticks


def test_year_ticks_sit_at_round_years():
    t0, p = Time("1990-03-01").jd, 0.5
    e_max = (Time("2020-03-01").jd - t0) / p
    ticks = year_ticks(t0, p, 0.0, e_max)
    years = [int(t) for _, t in ticks]
    assert 3 <= len(ticks) <= 8 and all(y % 5 == 0 for y in years) and years[0] >= 1990
    for e, text in ticks:
        assert abs(Time(t0 + e * p, format="jd").decimalyear - int(text)) < 1e-6


def test_no_year_axis_for_reduced_times():
    assert year_ticks(54000.0, 0.5, 0.0, 1e5) == []
    assert year_axis(54000.0, 0.5, np.array([0.0, 10.0]), "Year") is None
    assert year_axis(2451545.0, 0.5, np.array([0.0, 20000.0]), "Year").label == "Year"

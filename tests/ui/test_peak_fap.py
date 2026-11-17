"""UI-16.4: the peak table's FAP column: Lomb–Scargle peaks get Baluev's FAP, other methods "—"."""

import numpy as np

from astrowb import api
from astrowb.ui.lightcurve_fold import peak_table


def _search(method):
    rng = np.random.default_rng(1)
    t = np.sort(rng.uniform(0, 30, 400))
    y = np.sin(2 * np.pi * t / 0.7) + 0.1 * rng.normal(size=t.size)
    return api.run("timeseries.period", time=t.tolist(), flux=y.tolist(), method=method, p_min=0.1, p_max=5.0)


def test_lomb_scargle_top_peak_is_significant():
    table = peak_table(_search("lomb-scargle"))
    assert abs(table["period"][0] - 0.7) < 0.01
    assert float(table["fap"][0]) < 1e-10
    assert "e-" in table["fap"][0]  # below 0.001: scientific notation


def test_other_method_shows_a_dash_with_a_reason():
    table = peak_table(_search("pdm"))
    assert set(table["fap"]) == {"—"}
    assert "only for Lomb" in table["fap"].description

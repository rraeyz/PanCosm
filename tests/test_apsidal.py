"""OC-7: exact times of minima with apsidal motion, the fit from a grid, derived values."""

import numpy as np
import pytest

from astrowb.timeseries import apsidal as ap


@pytest.mark.parametrize("incl", [90.0, 80.0])
def test_the_exact_times_agree_with_the_first_order_displacement(incl):
    ps, e = 3.0, 0.01
    for w in (0.0, 45.0, 120.0):
        d = ap.times([0.5], 0, ps, e, w, 0, incl)[0] - ap.times([0], 0, ps, e, w, 0, incl)[0] - ps / 2
        first = ps / np.pi * e * np.cos(np.radians(w)) * (1 + 1 / np.sin(np.radians(incl)) ** 2)
        assert d == pytest.approx(first, abs=3 * e * e * ps)
    # the mean interval between primaries is the sidereal period
    t = ap.times(np.arange(0, 20000, 100.0), 0, ps, 0.3, 10, 360 / 20000, 86)
    assert (t[-1] - t[0]) / (19900) == pytest.approx(ps, rel=1e-4)


@pytest.mark.slow
def test_an_eccentric_system_is_recovered_from_the_grid():
    ps, rate = 3.0, 360 * 3.0 / (80 * 365.25)  # U = 80 yr
    rng = np.random.default_rng(1)
    cyc = np.sort(rng.choice(np.arange(int(40 * 365.25 / ps)), 150, replace=False)).astype(float)
    ep = np.concatenate([cyc[:75], cyc[75:] + 0.5])
    t = ap.times(ep, 2450000.0, ps, 0.25, 70.0, rate, 85.0) + rng.normal(0, 0.0003, ep.size)
    f = ap.fit(ep, t, np.full(ep.size, 0.0003), 85.0)
    for key, truth in (("e", 0.25), ("omega0", 70.0), ("d_omega", rate), ("Ps", ps)):
        assert abs(f[key] - truth) < 2 * f[key + "_err"], key
    d = ap.derived(f)
    assert d["U_years"] == pytest.approx(80, abs=3 * d["U_years_err"])
    assert f["map"].shape == (len(f["e_grid"]), len(f["rate_grid"]))


def test_derived_relativity_k2_and_limits():
    # a 3-day pair of 2 + 2 M☉: ω̇_rel ≈ 5.45e-4 (4/3)^(2/3)
    assert ap.relativistic(2, 2, 3.0, 0.0) == pytest.approx(5.45e-4 * (4 / 3) ** (2 / 3))
    k2 = ap.k2_observed(0.01, 0.1, 2.0, 1.8, 0.15, 0.13)
    assert 0.001 < k2 < 0.1
    with pytest.raises(ValueError):
        ap.fit([0, 1, 1.5], [0, 3, 4.5], [1e-3] * 3)

"""MOD-8: spots on the surface grids — a small spot against the analytic curve, and a cool spot's O'Connell
asymmetry recovered by a fit from a start 30° away."""

import numpy as np
import pytest
from scipy.optimize import minimize

from astrowb.models import roche, spots
from astrowb.models import roche_lc as lc
from astrowb.occult.laws import intensity as limb


def test_a_small_spot_follows_the_analytic_curve():
    s1 = lc.star(0.2, 1.0, ("linear", (0.6,)), n_theta=60)
    s2 = lc.star(0.01, 0.0, ("uniform", ()), n_theta=8, second=True)  # a dark point: no eclipse at i = 60°
    ph = np.linspace(0, 1, 49)
    deficit = lc.flux(ph, 60, s1, s2) - spots.flux(ph, 60, s1, s2, spots=([(60, 0, 3, 0.8)], ()))
    # the analytic small spot: its disc of area π (R sin ρ)² seen at μ, darkened by the law, with (1 − f⁴) less light
    i, a = np.radians(60), 2 * np.pi * ph
    view = np.stack([np.sin(i) * np.cos(a), -np.sin(i) * np.sin(a), np.full_like(a, np.cos(i))], axis=1)
    mu = np.clip(view @ [np.sin(np.radians(60)), 0, np.cos(np.radians(60))], 0, None)
    analytic = (1 - 0.8**4) * limb(mu, "linear", (0.6,)) * mu * np.pi * (0.2 * np.sin(np.radians(3))) ** 2
    assert np.max(np.abs(deficit - analytic)) < 0.02 * analytic.max()


def test_overlap_rules_and_limits():
    s = lc.star(0.2, 1.0, n_theta=20)
    two = [(90, 0, 30, 0.8), (90, 0, 10, 0.5)]
    f, _w = spots.factors(s, two, "product")
    assert f.min() == pytest.approx(0.4) and f.max() == 1.0
    f, _w = spots.factors(s, two, "later")
    assert f.min() == pytest.approx(0.5) and np.any(np.isclose(f, 0.8))
    with pytest.raises(ValueError):
        spots.factors(s, [two[0]] * 9)
    assert spots.longitude_at(10.0, 2.0, spin=1.25) == pytest.approx(190.0)
    assert spots.longitude_at(10.0, 3.0, drift=-5.0) == pytest.approx(355.0)


@pytest.mark.slow
def test_a_cool_spot_makes_the_oconnell_asymmetry_and_a_fit_finds_it():
    # shortcut: a close detached pair, not a contact one — the grids are not yet cut at the neck (MOD-3)
    q = 0.8
    s1 = lc.star(None, 1.0, ("linear", (0.6,)), 24, roche_q=q, om=roche.omega_for_volume_radius(0.33, q))
    om2 = roche.omega_for_volume_radius(0.29, 1 / q)
    s2 = lc.star(None, 0.9, ("linear", (0.6,)), 24, second=True, roche_q=1 / q, om=om2)
    ph = np.linspace(0, 1, 24, endpoint=False)

    def curve(lon, factor):
        return spots.flux(ph, 82, s1, s2, spots=([(90, lon, 20, factor)], ()), k=4)

    data = curve(90.0, 0.94)
    assert -2.5 * np.log10(data[6] / data[18]) == pytest.approx(-0.02, abs=0.002)  # maximum II fainter by 0.02 mag
    fit = minimize(lambda p: np.sum((curve(*p) - data) ** 2), [120.0, 0.9], method="Nelder-Mead",
                   options={"xatol": 0.01, "fatol": 1e-18})  # fmt: skip
    assert fit.x[0] == pytest.approx(90.0, abs=0.5) and fit.x[1] == pytest.approx(0.94, abs=0.002)

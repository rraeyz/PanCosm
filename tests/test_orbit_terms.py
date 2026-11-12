"""MOD-5: conjunction phases of an eccentric orbit, the ephemeris with a period change, pseudo-synchronism,
exposure integration and boosting."""

import numpy as np
import pytest
from scipy.optimize import brentq

from astrowb.models import eb, orbit_terms


def test_minima_of_an_eccentric_orbit_equal_the_conjunctions_found_numerically():
    e, w, p, t0 = 0.3, 60.0, 1.0, 0.0
    tp = eb.t_peri_from_t0(t0, p, e, w)

    def arg(t, target):  # ν + ω − target, wrapped
        nu = eb.true_anomaly(t, p, tp, e)
        return np.angle(np.exp(1j * (nu + np.radians(w) - target)))

    primary = brentq(arg, -0.2, 0.2, args=(np.pi / 2,), xtol=1e-14)
    guess = 0.5 + 2 / np.pi * e * np.cos(np.radians(w))
    secondary = brentq(arg, guess - 0.15, guess + 0.15, args=(3 * np.pi / 2,), xtol=1e-14)
    sec, peri = orbit_terms.conjunction_phases(e, w)
    assert primary == pytest.approx(0.0, abs=1e-9)
    assert sec == pytest.approx((secondary - primary) % 1, abs=1e-9)
    assert peri == pytest.approx((tp - t0) % 1, abs=1e-9)
    assert orbit_terms.conjunction_phases(0.0, 37.0)[0] == pytest.approx(0.5, abs=1e-12)


def test_the_ephemeris_with_a_period_change_round_trips():
    t0, p, dpde = 2450000.0, 0.8, 1e-8
    e = np.array([-20000.0, 0.0, 15000.0, 40000.0])
    t = t0 + p * e + 0.5 * dpde * e**2
    assert orbit_terms.cycle(t, t0, p, dpde) == pytest.approx(e, abs=1e-8)
    assert orbit_terms.cycle(t, t0, p) == pytest.approx((t - t0) / p)


def test_pseudo_synchronism_and_boosting():
    assert orbit_terms.pseudo_synchronous(0.0) == pytest.approx(1.0)
    assert orbit_terms.pseudo_synchronous(0.5) > 2  # faster than the mean motion near periastron
    assert orbit_terms.boosting(1.0, 30.0, 3.0) == pytest.approx(1 - 3 * 30 / 299792.458)


def test_a_30_minute_exposure_equals_a_fine_sum():
    model = lambda t: eb.light_curve(t, 2.0, 0.0, 0.1, 0.08, 89.0, 0.5, 0.0, 90.0, (0.4, 0.2), (0.4, 0.2))  # noqa: E731
    t = np.linspace(-0.06, 0.06, 41)
    got = orbit_terms.integrate_exposure(model, t, 30 / 1440)  # n chosen for 1e-6
    fine = orbit_terms.integrate_exposure(model, t, 30 / 1440, 2001)
    assert np.max(np.abs(got - fine)) < 1e-6

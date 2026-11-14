"""MOD-11: starting values from a folded light curve."""

import numpy as np
import pytest

from astrowb.models import eb, roche, spots
from astrowb.models import estimate as es
from astrowb.models import roche_lc as lc


def test_detached_systems():
    rng = np.random.default_rng(0)
    for _ in range(25):
        r1, r2 = rng.uniform(0.06, 0.18), rng.uniform(0.05, 0.12)
        e, w, j = rng.uniform(0, 0.2), rng.uniform(0, 360), rng.uniform(0.3, 1.0)
        ph = rng.uniform(0, 1, 3000)
        f = eb.light_curve(ph, 1.0, 0.0, r1, r2, 89.0, j, e, w, (0.5, 0.2), (0.5, 0.2))
        d = es.estimate(ph, f + rng.normal(0, 0.005, ph.size))
        assert d["ecosw"][0] == pytest.approx(e * np.cos(np.radians(w)), abs=0.01)
        assert d["r_sum"][0] == pytest.approx(r1 + r2, rel=0.35)  # a first guess: partial eclipses, e
        assert d["morphology"][0] == "detached"


def test_a_contact_system_and_a_spot():
    q = 0.4
    om = roche.omega_from_fillout(0.3, q)
    s1 = lc.star(None, 1.0, ("linear", (0.6,)), 20, roche_q=q, om=om)
    s2 = lc.star(None, 0.95, ("linear", (0.6,)), 20, second=True, roche_q=1 / q, om=om / q + (q - 1) / (2 * q))
    ph = np.linspace(0, 1, 120, endpoint=False)
    f = spots.flux(ph, 80, s1, s2, spots=([(90, 90, 20, 0.9)], ()), k=3)
    f = f / f.max() + np.random.default_rng(1).normal(0, 0.002, ph.size)
    d = es.estimate(ph, f)
    assert d["morphology"][0] == "contact"
    _diff, _err, spotted = es.oconnell(ph, f, d["model"][3])
    assert spotted


def test_start_values_from_a_curve_folded_on_the_ephemeris():
    """UF-20: r1 + r2 and J start from the folded curve, not from the table's defaults; an empty or too short curve
    gives nothing."""
    rng = np.random.default_rng(2)
    t = np.sort(rng.uniform(2459500, 2459506, 900))
    f = eb.light_curve(
        ((t - 2459500.25) / 1.7) % 1.0, 1.0, 0.0, 0.14, 0.1, 88.0, 0.6, 0.0, 90.0, (0.4, 0.2), (0.4, 0.2)
    )
    got = es.start_from_curve(t, f + rng.normal(0, 0.003, t.size), 1.7, 2459500.25)
    assert got["r_sum"] == pytest.approx(0.24, rel=0.4) and 0.2 < got["j"] < 1.5
    assert es.start_from_curve(t[:5], f[:5], 1.7, 2459500.25) == {} and es.start_from_curve(t, f, None, 0.0) == {}

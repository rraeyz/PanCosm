"""MOD-3: the light curve of two surface grids — two spheres against the analytic eclipse model, a Roche pair's
ellipsoidal variation, smoothness in the inclination."""

import numpy as np
import pytest

from astrowb.models import eb, roche
from astrowb.models import roche_lc as lc

R1, R2, J = 0.2, 0.15, 0.6
LD1, LD2 = (0.4, 0.2), (0.5, 0.15)
PHASES = np.r_[np.linspace(-0.06, 0.06, 25), np.linspace(0.44, 0.56, 25), 0.25]


@pytest.mark.parametrize(("n_theta", "limit"), [(60, 3e-5), (90, 2.5e-5)])  # "normal" and "fine", measured
@pytest.mark.parametrize("incl", [90.0, 86.0, 80.0])  # annular / total, partial deep, partial shallow
def test_two_spheres_equal_the_analytic_eclipses(n_theta, limit, incl):
    s1 = lc.star(R1, 1.0, ("quadratic", LD1), n_theta=n_theta)
    s2 = lc.star(R2, J, ("quadratic", LD2), n_theta=n_theta, second=True)
    f = lc.flux(PHASES, incl, s1, s2)
    ref = eb.light_curve(PHASES, 1.0, 0.0, R1, R2, incl, J, 0.0, 90.0, LD1, LD2)
    assert np.max(np.abs(f / f[-1] - ref)) < limit


def roche_pair(q=0.8, r1=0.3, r2=0.26, n_theta=30):
    s1 = lc.star(None, 1.0, ("quadratic", LD1), n_theta, roche_q=q, om=roche.omega_for_volume_radius(r1, q))
    om2 = roche.omega_for_volume_radius(r2, 1 / q)  # star 2 in its own frame: mass ratio 1/q
    s2 = lc.star(None, 0.9, ("quadratic", LD2), n_theta, second=True, roche_q=1 / q, om=om2)
    return s1, s2


def test_a_roche_pair_shows_ellipsoidal_light_without_eclipses():
    s1, s2 = roche_pair()
    f = lc.flux([0.0, 0.125, 0.25, 0.5], 40.0, s1, s2)  # i = 40°: no eclipse
    assert f[2] > f[1] > f[0] and f[2] > f[3]  # brightest at quadrature, where the stretched stars show their sides
    assert 0.01 < f[2] / f[0] - 1 < 0.2


def test_the_flux_is_smooth_in_the_inclination():
    s1 = lc.star(R1, 1.0, ("quadratic", LD1), n_theta=40)
    s2 = lc.star(R2, J, ("quadratic", LD2), n_theta=40, second=True)
    incl = np.linspace(84.0, 84.5, 60)
    f = np.array([lc.flux([0.01], i, s1, s2)[0] for i in incl])
    second = np.abs(np.diff(f, 2))
    assert second.max() < 20 * np.median(second) + 1e-9  # no jumps where elements change state

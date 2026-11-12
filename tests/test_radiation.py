"""MOD-2: disc fluxes of every limb-darkening law in closed form, gravity-darkened temperatures, band-integrated
blackbody intensities."""

import numpy as np
import pytest

from astrowb.models import radiation, roche
from astrowb.occult import laws

LAWS = {"uniform": (), "linear": (0.6,), "quadratic": (0.4, 0.25), "sqrt": (0.3, 0.4), "log": (0.6, 0.2),
        "power2": (0.6, 0.6), "nonlinear": (0.5, -0.2, 0.6, -0.25)}  # fmt: skip


@pytest.mark.parametrize("law", list(LAWS))
def test_disc_flux_closed_form_equals_the_integral(law):
    from scipy.integrate import quad

    c = LAWS[law]
    numeric = quad(lambda mu: laws.intensity(mu, law, c) * 2 * mu, 0, 1, epsabs=1e-14, epsrel=1e-13)[0]
    assert laws.disc_flux(law, c) == pytest.approx(numeric, abs=1e-10)


def test_gravity_darkened_temperatures_keep_the_effective_temperature():
    om = roche.omega_for_volume_radius(0.35, 0.6)
    s = roche.surface(om, 0.6, n_theta=24)
    t = radiation.temperatures(s["gravity"], s["area"], 6000.0, beta=0.08)
    mean = (np.sum(s["area"] * t**4) / np.sum(s["area"])) ** 0.25
    assert mean == pytest.approx(6000.0, abs=0.01)
    assert t[np.argmax(s["xyz"][:, 2])] > t[np.argmax(s["xyz"][:, 0])]  # the pole hotter than the nose


def test_band_intensity_equals_adaptive_quadrature():
    from scipy.integrate import quad

    w = np.array([480.0, 500, 550, 600, 650, 680])  # a V-like band, response linear between its points
    r = np.array([0.0, 0.4, 1.0, 0.7, 0.2, 0.0])
    for t in (3500.0, 5800.0, 20000.0):
        num = quad(
            lambda x, t=t: radiation.planck(x, t) * np.interp(x, w, r), w[0], w[-1], points=w[1:-1], epsrel=1e-12
        )[0]
        den = quad(lambda x: np.interp(x, w, r), w[0], w[-1], points=w[1:-1], epsrel=1e-12)[0]
        assert radiation.band_intensity(t, w, r) == pytest.approx(num / den, rel=1e-8)

"""EXO-1: the occultation kernel against closed forms and an independent integration, continuous at every contact;
the transit model's depth, duration, exposure integration, dilution and occultation."""

import numpy as np
import pytest

from astrowb.occult import laws
from astrowb.occult.flux import occulted_fraction
from astrowb.occult.model import transit

LAWS = {"uniform": (), "linear": (0.6,), "quadratic": (0.4, 0.25), "sqrt": (0.3, 0.4), "log": (0.6, 0.2),
        "power2": (0.6, 0.6), "nonlinear": (0.5, -0.2, 0.6, -0.25)}  # fmt: skip


def overlap(z, k):
    """The uniform disc's hidden fraction: the area two circles share (closed form) over π."""
    z = np.asarray(z, float)
    out = np.where(z <= k - 1, 1.0, np.where(z <= 1 - k, k * k, 0.0))
    part = (z > abs(1 - k)) & (z < 1 + k)
    zz = z[part]
    k0 = np.arccos(np.clip((k * k + zz * zz - 1) / (2 * k * zz), -1, 1))
    k1 = np.arccos(np.clip((1 - k * k + zz * zz) / (2 * zz), -1, 1))
    out[part] = (k * k * k0 + k1 - 0.5 * np.sqrt(np.clip(4 * zz * zz - (1 + zz * zz - k * k) ** 2, 0, None))) / np.pi
    return out


@pytest.mark.parametrize("k", [0.001, 0.01, 0.1, 0.5, 0.99, 1.2, 2.0])
def test_uniform_disc_equals_the_closed_form(k):
    z = np.linspace(0, 3, 3001)
    assert np.max(np.abs(occulted_fraction(z, k, "uniform", ()) - overlap(z, k))) < 1e-8


def test_every_law_equals_an_independent_adaptive_integration():
    from scipy.integrate import quad

    rng = np.random.default_rng(1)
    for law, c in LAWS.items():
        norm = laws.disc_flux(law, c) * np.pi
        for _ in range(8):
            k, z = rng.uniform(0.01, 0.5), rng.uniform(0, 1.6)

            def ring(r, k=k, z=z):
                if z == 0:
                    return 2 * np.pi * r * (r < k)
                cos = (r * r + z * z - k * k) / (2 * r * z) if r > 0 else 2.0
                return (
                    2 * r * np.arccos(np.clip(cos, -1, 1)) if abs(r - z) < k else (2 * np.pi * r if r < k - z else 0.0)
                )

            def integrand(r, law=law, c=c, ring=ring):
                return laws.intensity(np.sqrt(max(1 - r * r, 0)), law, c) * ring(r)

            stops = [x for x in (abs(z - k), z + k) if 0 < x < 1]
            ref = quad(integrand, 0, 1, points=stops or None, limit=400, epsabs=1e-12)[0] / norm
            assert occulted_fraction([z], k, law, c)[0] == pytest.approx(ref, abs=1e-7), (law, k, z)


def test_no_jump_at_any_contact():
    for law, c in LAWS.items():
        for k in (0.1, 0.7):
            for z in (1 - k, 1 + k - 1e-9, k, abs(1 - k)):
                a, b = occulted_fraction([z - 1e-10, z + 1e-10], k, law, c)
                assert abs(a - b) < 1e-8, (law, k, z)


def test_laws_check_their_coefficients_and_convert():
    assert laws.problem("quadratic", (0.4, 0.25)) is None
    assert "negative" in laws.problem("quadratic", (1.2, 0.3))
    assert "brighter" in laws.problem("linear", (-0.5,))
    q1, q2 = laws.u_to_q(0.4, 0.25)
    assert laws.q_to_u(q1, q2) == pytest.approx((0.4, 0.25))
    with pytest.raises(ValueError, match="takes 2"):
        laws.intensity(0.5, "quadratic", (0.1,))


def test_a_transit_has_its_depth_duration_and_secondary_eclipse():
    p, tc, k, a, inc = 3.0, 0.0, 0.1, 10.0, 90.0
    t = np.linspace(-0.2, 0.2, 4001)
    f = transit(t, p, tc, k, a, inc, "uniform", ())
    assert 1 - f.min() == pytest.approx(k * k, rel=1e-6)
    t14 = p / np.pi * np.arcsin(np.sqrt((1 + k) ** 2) / a)  # central, circular
    inside = t[f < 1]
    assert np.ptp(inside) == pytest.approx(t14, abs=2 * (t[1] - t[0]))
    occ = transit(np.array([p / 2, p / 4]), p, tc, k, a, inc, "uniform", (), occultation=1e-3)
    assert occ[0] == pytest.approx(1 / 1.001, rel=1e-9) and occ[1] == pytest.approx(1.0)
    diluted = transit(np.array([0.0]), p, tc, k, a, inc, "uniform", (), third_light=0.5)[0]
    assert 1 - diluted == pytest.approx(0.5 * k * k, rel=1e-6)


def test_exposures_are_the_average_of_the_curve_over_them():
    p, tc, k, a, inc = 3.0, 0.0, 0.1, 10.0, 88.0
    t = np.linspace(-0.12, 0.12, 49)
    exposure = 30 / 1440
    got = transit(t, p, tc, k, a, inc, "quadratic", (0.4, 0.25), exposure=exposure)
    mid = ((np.arange(4000) + 0.5) / 4000 - 0.5) * exposure  # the midpoint rule, very fine
    fine = np.array([transit(ti + mid, p, tc, k, a, inc, "quadratic", (0.4, 0.25)).mean() for ti in t])
    assert np.max(np.abs(got - fine)) < 1e-6

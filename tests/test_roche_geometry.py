"""MOD-1: the Roche potential's critical points and radii against closed forms and independent approximations."""

import numpy as np
import pytest

from astrowb.models import roche


def eggleton(q):
    """Eggleton 1983 (ApJ 268, 368): star 1's Roche-lobe volume radius / a, to 1 %; here q = M2/M1."""
    qe = 1 / q
    return 0.49 * qe ** (2 / 3) / (0.6 * qe ** (2 / 3) + np.log(1 + qe ** (1 / 3)))


def test_equal_masses_put_l1_halfway_and_omega_in_at_three_and_three_quarters():
    l1, l2, l3 = roche.lagrange(1.0)
    assert l1 == pytest.approx(0.5, abs=1e-12) and l2 == pytest.approx(1 - l3, abs=1e-9)  # mirror images
    assert roche.critical(1.0)[0] == pytest.approx(3.75, abs=1e-12)  # 2 + 2 − 0.5 + 0.25


@pytest.mark.parametrize("q", [0.1, 0.3, 0.6, 1.0])
def test_the_roche_lobe_volume_radius_matches_eggleton_within_one_percent(q):
    om_in = roche.critical(q)[0]
    assert roche.volume_radius(om_in * (1 + 1e-9), q) == pytest.approx(eggleton(q), rel=0.01)


def test_a_small_companion_leaves_a_sphere_and_radii_round_trip():
    r = roche.radii(100.0, 1e-6)  # q → 0 and a small star: Ω ≈ 1/r, rotation adds 5e-7 of it
    assert all(v == pytest.approx(0.01, rel=1e-5) for v in r.values())
    om = roche.omega_for_volume_radius(0.3, 0.5)
    assert roche.volume_radius(om, 0.5) == pytest.approx(0.3, abs=1e-9)
    r = roche.radii(om, 0.5)
    assert r["pole"] < r["side"] < r["back"] < r["point"]  # tidally and rotationally stretched


def test_fillout_marks_the_two_critical_surfaces():
    om_in, om_out = roche.critical(0.4)
    assert roche.fillout(om_in, 0.4) == pytest.approx(0.0) and roche.fillout(om_out, 0.4) == pytest.approx(1.0)
    assert roche.omega_from_fillout(0.5, 0.4) == pytest.approx((om_in + om_out) / 2)
    with pytest.raises(ValueError, match="not closed"):
        roche.radius(om_out * 0.9, 0.4, 0.0, 0.0)


def test_the_surface_grid_of_a_sphere_and_of_a_stretched_star():
    s = roche.surface(100.0, 1e-6, n_theta=30)  # a small star: a sphere of r = 0.01
    assert s["total_area"] == pytest.approx(4 * np.pi * 1e-4, rel=1e-4)
    assert s["volume"] == pytest.approx(4 / 3 * np.pi * 1e-6, rel=1e-4)
    assert np.allclose(np.sum(s["normal"] * s["xyz"], axis=1) / np.linalg.norm(s["xyz"], axis=1), 1, atol=1e-4)
    om = roche.omega_for_volume_radius(0.35, 0.6)
    t = roche.surface(om, 0.6, n_theta=30)
    assert (3 * t["volume"] / (4 * np.pi)) ** (1 / 3) == pytest.approx(0.35, rel=2e-3)  # the same star two ways
    pole = t["gravity"][np.argmax(t["xyz"][:, 2])]
    nose = t["gravity"][np.argmax(t["xyz"][:, 0])]
    assert pole > nose  # weakest gravity towards the companion, where gravity darkening dims the star most
    assert t["total_area"] > 4 * np.pi * 0.35**2  # a stretched star has more surface than its sphere

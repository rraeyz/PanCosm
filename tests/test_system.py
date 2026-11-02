"""MOD-10: parameterisations round-trip, morphology constraints hold after any edit, checks, the system file."""

import numpy as np
import pytest

from astrowb.models import roche
from astrowb.models import system as sm


def test_parameterisations_round_trip():
    rng = np.random.default_rng(0)
    for _ in range(200):
        r1, r2 = rng.uniform(0.05, 0.4, 2)
        assert np.allclose(sm.sum_ratio_to_radii(*sm.radii_to_sum_ratio(r1, r2)), (r1, r2), rtol=0, atol=1e-12)
        e, w = rng.uniform(0.001, 0.9), rng.uniform(0, 360)
        assert np.allclose(sm.cos_sin_to_e_w(*sm.e_w_to_cos_sin(e, w)), (e, w), atol=1e-10)
        assert np.allclose(sm.sqrt_to_e_w(*sm.e_w_to_sqrt(e, w)), (e, w), atol=1e-10)
        q, om = rng.uniform(0.1, 3), rng.uniform(3, 20)
        assert sm.from_own_frame(sm.to_own_frame(om, q), q) == pytest.approx(om, abs=1e-10)
    q = 0.7
    om = roche.omega_for_volume_radius(0.27, q)
    assert roche.volume_radius(om, q) == pytest.approx(0.27, abs=1e-10)
    f = roche.fillout(roche.omega_from_fillout(0.4, q), q)
    assert f == pytest.approx(0.4, abs=1e-10)


@pytest.mark.parametrize("morphology", ["semi-detached-1", "semi-detached-2", "contact"])
def test_constraints_hold_after_random_edits(morphology):
    s = sm.default_system()
    s.morphology = morphology
    s.params["fillout"].value = 0.3
    s.apply()
    rng = np.random.default_rng(1)
    for _ in range(30):
        s.set("q", rng.uniform(0.2, 1.5))
        s.set("fillout", rng.uniform(0.05, 0.9))
        q = s["q"]
        if morphology == "semi-detached-1":
            assert s["omega1"] == pytest.approx(roche.critical(q)[0], abs=1e-12)
        elif morphology == "semi-detached-2":
            assert s["omega2"] == pytest.approx(roche.critical(1 / q)[0], abs=1e-12)
        else:
            assert roche.fillout(s["omega1"], q) == pytest.approx(s["fillout"], abs=1e-10)
            assert sm.from_own_frame(s["omega2"], q) == pytest.approx(s["omega1"], abs=1e-10)
    assert "omega1" not in s.free() or morphology == "semi-detached-2"
    with pytest.raises(ValueError):
        sm.System(s.params, morphology="overcontact").apply()


def test_checks_and_the_system_file():
    s = sm.default_system()
    s.params["omega1"].value = roche.critical(0.8)[0] - 0.1  # beyond its lobe
    s.data.append(sm.DataSet("lc", np.array([5000.0, 5000.5]), np.ones(2), band="V"))
    s.params["l3"].free = True
    codes = sm.check(s, partial_eclipse=True)
    assert {"BEYOND_LOBE", "T0_FAR", "L3_INCL"} <= set(codes) and all(c in sm.CHECKS for c in codes)
    s.params["incl"].prior = ("gaussian", 85.0, 2.0)
    back = sm.from_toml(sm.to_toml(s))
    for k, p in s.params.items():
        b = back.params[k]
        assert (b.value, b.free, b.lower, b.upper, b.prior, b.unit) == (p.value, p.free, p.lower, p.upper, p.prior,
                                                                       p.unit)  # fmt: skip
    assert back.morphology == "detached"

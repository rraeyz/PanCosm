"""PHO-28: the night's solution from standard stars — k′ = 0.25, colour term 0.08, zero point 21.3 recovered within
1σ; programme stars put on the standard system."""

import numpy as np
import pytest

from astrowb.photometry import allsky

Z, K, T = 21.3, 0.25, 0.08


def standards(n=120, seed=4, noise=0.01, outliers=3):
    rng = np.random.default_rng(seed)
    X = rng.uniform(1.05, 2.4, n)  # several fields through the night
    C = rng.uniform(-0.1, 1.6, n)
    M = rng.uniform(9, 14, n)
    m = M - (Z - K * X + T * C) + rng.normal(0, noise, n)
    m[:outliers] += 0.4  # a few bad measures (a cosmic ray, a neighbour)
    return m, M, X, C


def test_the_coefficients_are_recovered_within_their_errors():
    m, M, X, C = standards()
    sol = allsky.fit(m, M, X, C, err=np.full(len(m), 0.01))
    for term, truth in (("zero_point", Z), ("extinction", K), ("colour", T)):
        assert abs(sol.coef[term] - truth) < 2.5 * sol.error[term], term  # within the errors
        assert sol.error[term] < 0.02
    assert not sol.used[:3].any() and sol.used[3:].all()  # the bad ones clipped
    assert allsky.night_quality(sol)["photometric"] and sol.rms < 0.012


def test_programme_stars_in_two_filters():
    B, V = np.array([12.8, 13.9]), np.array([12.0, 12.6])
    Xa, Xb = np.array([1.3, 1.8]), np.array([1.32, 1.82])
    sol_b = allsky.Solution({"zero_point": 20.9, "extinction": 0.35, "colour": 0.05}, dict.fromkeys(("zero_point",
                            "extinction", "colour"), 0.0), np.zeros((3, 3)), ("zero_point", "extinction", "colour"),
                            0.01, np.ones(1, bool))  # fmt: skip
    sol_v = allsky.Solution({"zero_point": Z, "extinction": K, "colour": T}, dict.fromkeys(sol_b.terms, 0.0),
                            np.zeros((3, 3)), sol_b.terms, 0.01, np.ones(1, bool))  # fmt: skip
    b = B - sol_b.correction(Xa, B - V)
    v = V - sol_v.correction(Xb, B - V)
    got_b, got_v, colour = allsky.apply_pair(sol_b, sol_v, b, v, Xa, Xb)
    assert got_b == pytest.approx(B, abs=1e-6) and got_v == pytest.approx(V, abs=1e-6)
    assert colour == pytest.approx(B - V, abs=1e-6)


def test_a_cloudy_night_is_not_photometric():
    m, M, X, C = standards(noise=0.06, outliers=0)
    sol = allsky.fit(m, M, X, C)
    assert not allsky.night_quality(sol)["photometric"]

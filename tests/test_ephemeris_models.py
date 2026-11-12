"""OC-5: ephemeris models, their comparison, robust fits, the observers' form."""

import numpy as np
import pytest

from astrowb.timeseries import ephemeris_models as em

T0, P = 2455000.1234, 0.3651234


def minima(seed, q=0.0, jump=None, n=120, sigma=0.0004, secondary=False):
    rng = np.random.default_rng(seed)
    e = np.sort(rng.choice(np.arange(-12000, 12000), n, replace=False)).astype(float)
    if secondary:
        e[::3] += 0.5
    t = T0 + P * e + q * e**2
    if jump is not None:
        t += jump[1] * np.maximum(e - jump[0], 0)
    return t + rng.normal(0, sigma, n), e, np.full(n, sigma)


def test_a_period_change_is_measured_with_honest_errors():
    q = 2e-10  # dP/dt = 2Q/P
    inside1 = inside2 = 0
    for seed in range(200):
        t, e, s = minima(seed, q=q)
        f = em.fit(t, e, s, order=2)
        rate, err, _ = em.dp_dt(f)
        truth = 2 * q / P * em.SECONDS_PER_YEAR
        inside1 += abs(rate - truth) < err
        inside2 += abs(rate - truth) < 2 * err
    assert 0.60 <= inside1 / 200 <= 0.76 and inside2 / 200 >= 0.92


def test_the_f_test_seldom_wants_a_parabola_on_linear_data():
    rejected = 0
    for seed in range(200):
        t, e, s = minima(seed)
        _f, prob = em.f_test(em.fit(t, e, s, 1), em.fit(t, e, s, 2))
        rejected += prob < 0.01
    assert rejected / 200 <= 0.02
    t, e, s = minima(1, q=2e-10)
    lin, par = em.fit(t, e, s, 1), em.fit(t, e, s, 2)
    assert em.f_test(lin, par)[1] < 1e-10
    rows, verdict = em.compare({"linear": lin, "quadratic": par})
    assert verdict.startswith("quadratic is preferred: ΔBIC = -") and len(rows) == 2


def test_a_period_jump_is_found_where_it_happened():
    hits = 0
    for seed in range(50):
        t, e, s = minima(seed, jump=(3000.0, 1e-6))
        f = em.segmented(t, e, s, 1, grid=240)
        p0, p1 = f["periods"]
        hits += abs(f["breaks"][0] - 3000) < 300 and abs(p1 - p0 - 1e-6) < 3 * np.sqrt(f["cov"][2, 2])
    assert hits >= 45
    assert f["jumps"][0] == pytest.approx(1e-6 / P, rel=0.1)
    two = em.segmented(*minima(1, jump=(-5000.0, 1e-6))[:3], 2, grid=60)
    assert len(two["breaks"]) == 2 and len(two["periods"]) == 3


def test_robust_fits_ignore_outliers():
    t, e, s = minima(3)
    t[[5, 50, 90]] += [0.01, -0.02, 0.015]  # three wrong minima, 25-50 σ off
    plain = em.fit(t, e, s, 1)
    clip = em.fit(t, e, s, 1, robust="clip")
    huber = em.fit(t, e, s, 1, robust="huber")
    assert plain["chi2r"] > 20 and clip["chi2r"] < 1.5
    assert set(np.flatnonzero(~clip["used"])) == {5, 50, 90}
    assert clip["coef"][1] == pytest.approx(P, abs=3 * clip["err"][1])
    assert huber["coef"][1] == pytest.approx(P, abs=5 * clip["err"][1])
    w = em.weights_by_method(["visual", "Electronic", "ccd?"])
    assert list(w) == [1.0, 10.0, 1.0]


def test_secondary_offset_epochs_and_the_observers_form():
    t, e, s = minima(4, secondary=True)
    delta = 0.002  # the secondaries late by 0.002 d: e cos ω = (π/2)(δ/P)
    t[np.abs(e % 1 - 0.5) < 1e-6] += delta
    f = em.fit(t, e, s, 1, secondary_offset=True)
    ec, ec_err = em.ecosw(f)
    assert ec == pytest.approx(np.pi / 2 * delta / P, abs=4 * ec_err)
    t0, t0_err, p, p_err, at = em.updated(f, "middle")
    assert p == pytest.approx(P, abs=4 * p_err) and t0 == pytest.approx(T0 + P * at, abs=5 * t0_err)
    text = em.observer_form(2459000.123456, 0.00012, 0.365123451, 0.000000031)
    assert text == "Min I = BJD_TDB 2459000.12346(12) + 0.365123451(31) E"
    late = np.array([T0 + 0.3 * P, T0 + 5 * P])
    assert list(em.ambiguous(late, [0, 5], T0, P)) == [0]
    assert em.mass_transfer(1e-7 * em.SECONDS_PER_YEAR / 365.25, 0.4, 1.4, 0.4) > 0
    with pytest.raises(ValueError):
        em.mass_transfer(1.0, 0.4, 1.0, 1.0)

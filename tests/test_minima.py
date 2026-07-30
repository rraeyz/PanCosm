import numpy as np
import pytest

from astrowb.timeseries.minima import kwee_van_woerden, o_minus_c, polynomial_minimum

T_TRUE = 2458107.6123


def eclipse(t, depth=0.3, width=0.02):
    return 1 - depth * np.exp(-0.5 * ((t - T_TRUE) / width) ** 2)


@pytest.mark.parametrize("method", ["kvw", "poly"])
def test_recovers_minimum_and_honest_errors(method):
    rng = np.random.default_rng(3)
    t = T_TRUE + np.linspace(-0.06, 0.05, 120) + 0.0004  # asymmetric coverage on purpose
    estimates, errors = [], []
    for _ in range(200):
        y = eclipse(t) + rng.normal(0, 0.01, t.size)
        if method == "kvw":
            tm, s_kvw, s_boot = kwee_van_woerden(t, y, bootstrap=40)
            errors.append(max(s_kvw, s_boot))
        else:
            sel = np.abs(t - T_TRUE) < 0.02
            tm, s = polynomial_minimum(t[sel], y[sel])
            errors.append(s)
        estimates.append(tm)
    estimates = np.array(estimates)
    scatter = estimates.std()
    assert abs(estimates.mean() - T_TRUE) < 3 * scatter / np.sqrt(len(estimates)) + 2e-5  # unbiased
    ratio = np.median(errors) / scatter
    assert 0.6 < ratio < 2.0, f"reported error / true scatter = {ratio:.2f}"


def test_kvw_noise_free_exact():
    t = np.linspace(T_TRUE - 0.05, T_TRUE + 0.05, 101)
    tm, _, _ = kwee_van_woerden(t, eclipse(t), bootstrap=0)
    assert abs(tm - T_TRUE) * 86400 < 0.5  # < 0.5 s


def test_o_minus_c():
    t0, p = 2455867.402743, 2.1500082
    epochs, oc = o_minus_c([t0 + 1050 * p + 0.001, t0 - 3 * p - 0.002], t0, p)
    assert epochs.tolist() == [1050, -3]
    np.testing.assert_allclose(oc, [0.001, -0.002], atol=1e-9)


def test_one_sided_data_rejected():
    t = np.linspace(0, 1, 50)
    with pytest.raises(ValueError):
        kwee_van_woerden(t, t, bootstrap=0)  # minimum at the edge


def transit(t, depth=0.022, t14=0.125, tin=0.014):
    x = np.abs(t - T_TRUE)
    return 1 - depth * np.clip((t14 / 2 - x) / tin, 0, 1)


def test_trapezoid_fit_recovers_transit_with_honest_errors():
    from astrowb.timeseries.minima import trapezoid_fit

    rng = np.random.default_rng(5)
    t = T_TRUE + np.linspace(-0.14, 0.11, 140)
    fits_ = [trapezoid_fit(t, transit(t) * 1.3 + rng.normal(0, 0.008, t.size)) for _ in range(150)]
    t0 = np.array([f["t0"] for f in fits_])
    assert abs(t0.mean() - T_TRUE) * 86400 < 3 * t0.std() * 86400 / np.sqrt(150) + 5
    assert 0.7 < np.median([f["t0_err"] for f in fits_]) / t0.std() < 1.5
    assert abs(np.median([f["depth"] for f in fits_]) - 0.022) < 0.002
    assert abs(np.median([f["t14"] for f in fits_]) - 0.125) < 0.005


def test_kvw_rarely_fails_on_flat_bottomed_transits():
    rng = np.random.default_rng(5)
    t = T_TRUE + np.linspace(-0.14, 0.11, 140)
    fails = 0
    for _ in range(100):
        try:
            kwee_van_woerden(t, transit(t) + rng.normal(0, 0.008, t.size), bootstrap=0)
        except ValueError:
            fails += 1
    assert fails <= 5  # reported as "no minimum found"; the trapezoid fit is the tool for transits

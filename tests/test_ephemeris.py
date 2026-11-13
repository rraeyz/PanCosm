import numpy as np
import pytest

from astrowb.timeseries.ephemeris import SECONDS_PER_YEAR, Minimum, epochs, fit, parse_minima

T0, P = 2450000.1234, 0.8765432


def test_parse_formats():
    text = """# BJD error type source
    BJD  ERR  TYPE
    2450000.1234 0.0002 I  ref A
    2450000.56167,0.0003,II
    2450001.0 p
    2450001.43827\t0.0001\ts\tB
    """
    m = parse_minima(text)
    assert [x.kind for x in m] == ["I", "II", "I", "II"]
    assert m[0].error == 0.0002 and m[0].source == "ref A" and m[2].error is None
    with pytest.raises(ValueError, match="line"):
        parse_minima("2450000.1\nabc 0.1")


def test_secondary_epochs_are_half_integers():
    m = [Minimum(T0 + 10 * P), Minimum(T0 + 10.5 * P + 0.001, kind="II"), Minimum(T0 - 3 * P)]
    assert epochs(m, T0, P).tolist() == [10, 10.5, -3]


def _synthetic(q=0.0, n=60, noise=0.0004, seed=1):
    rng = np.random.default_rng(seed)
    e = np.sort(rng.choice(np.arange(-8000, 8000), n, replace=False)).astype(float)
    times = T0 + P * e + q * e**2 + rng.normal(0, noise, n)
    return [Minimum(t, noise) for t in times], e


def test_linear_fit_recovers_ephemeris_and_errors():
    minima, e = _synthetic()
    f = fit(minima, T0 + 0.01, P + 2e-6)  # a slightly wrong reference ephemeris is fine
    assert abs(f.period - P) < 3 * f.period_err
    assert abs(f.t0 - T0) < 3 * f.t0_err
    assert 0.5 < f.chi2r < 1.6
    # independent check: numpy weighted polyfit in the same epoch numbering gives the same numbers
    coef, cov = np.polyfit(f.epochs, [m.time - T0 for m in minima], 1, w=np.full(len(e), 1 / 0.0004), cov="unscaled")
    assert abs(coef[0] - f.period) < 1e-12 and abs(coef[1] + T0 - f.t0) < 1e-8  # 1 ms
    assert abs(np.sqrt(cov[1, 1]) / f.t0_err - 1) < 0.3  # same T0 error (ours scaled by chi2r only if > 1)
    # O-C relative to the reference ephemeris; the fitted line drawn in it passes through the points
    np.testing.assert_allclose(f.o_minus_c - f.model_o_minus_c(f.epochs), f.residuals, atol=1e-9)


def test_quadratic_fit_recovers_period_change():
    q = 1.0e-10  # days per cycle^2: 0.006 d at the ends of the data
    minima, _ = _synthetic(q=q)
    f = fit(minima, T0, P, order=2)
    assert abs(f.q - q) < 3 * f.q_err
    true_dpdt = 2 * q / P * SECONDS_PER_YEAR
    assert abs(f.dp_dt - true_dpdt) < 3 * f.dp_dt_err
    lin = fit(minima, T0, P, order=1)
    assert lin.chi2r > 5 * f.chi2r  # the parabola is clearly needed


def test_errors_scaled_when_scatter_exceeds_stated_errors():
    minima, _ = _synthetic(noise=0.002)
    for m in minima:
        m.error = 0.0004  # stated errors 5x too small
    f = fit(minima, T0, P)
    honest = fit([Minimum(m.time, 0.002) for m in minima], T0, P)
    assert f.chi2r > 10
    assert abs(f.period_err / honest.period_err - 1) < 0.3


def test_hjd_without_a_time_scale_is_named():
    """ARC-15 item 4: HJD with no scale gives TT − UTC of the latest time (69.184 s since 2017); a named scale none."""
    from astrowb.timeseries.ephemeris import hjd_scale_unknown

    assert hjd_scale_unknown("# HJD   error  type\n2459000.5 0.001 I", [2459000.5]) == pytest.approx(69.184, abs=0.01)
    assert hjd_scale_unknown("# HJD\n2451000.5", [2451000.5]) == pytest.approx(63.184, abs=0.01)  # 1998: 31 leap s
    assert hjd_scale_unknown("# HJD_UTC\n2459000.5", [2459000.5]) is None
    assert hjd_scale_unknown("# HJD (TT)\n2459000.5", [2459000.5]) is None
    assert hjd_scale_unknown("# BJD_TDB\n2459000.5", [2459000.5]) is None

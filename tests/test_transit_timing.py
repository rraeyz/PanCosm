"""OC-13: transit times — the drift of a linear ephemeris, orbital decay, the tidal quality factor."""

import numpy as np
import pytest

from astrowb.timeseries import transit_timing as tt

P, T0 = 1.09142, 2457010.512


def transits(seed, pdot_ms_yr=0.0, n=120, sigma=0.0004):
    rng = np.random.default_rng(seed)
    e = np.sort(rng.choice(np.arange(-2000, 2500), n, replace=False)).astype(float)
    dpde = pdot_ms_yr / 1000 / tt.em.SECONDS_PER_YEAR * P  # days per cycle
    return T0 + P * e + 0.5 * dpde * e * e + rng.normal(0, sigma, n), np.full(n, sigma)


def test_decay_is_measured_and_a_linear_system_shows_none():
    t, s = transits(1, pdot_ms_yr=-30.0)  # WASP-12 b-like
    got = tt.decay(t, s, T0, P)
    assert got["dp_dt_ms_yr"] == pytest.approx(-30.0, abs=4 * got["dp_dt_err"]) and got["delta_bic"] < -10
    false = sum(tt.decay(*transits(seed), T0, P)["f_test_p"] < 0.01 for seed in range(100))
    assert false <= 4


def test_the_drift_grows_with_the_epoch_and_the_quality_factor():
    t, s = transits(2)
    lin = tt.decay(t, s, T0, P)["linear"]
    d = tt.drift(lin, [0, 1000, 10000])
    assert d[0] < d[1] < d[2] and d[2] == pytest.approx(10000 * lin["err"][1], rel=0.1)
    # WASP-12: Ṗ = −29 ms/yr, M_p = 1.47 M_Jup, M★ = 1.43, R★ = 1.66, a = 0.0234 AU → Q′★ ≈ 1.8e5 (Yee et al. 2020)
    assert tt.tidal_q(-29.0, 1.0914, 1.47, 1.43, 1.66, 0.0234) == pytest.approx(1.8e5, rel=0.25)

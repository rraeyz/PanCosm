import numpy as np
import pytest

from astrowb.timeseries.period import bls, fold, lomb_scargle, pdm


@pytest.fixture
def sampling():
    rng = np.random.default_rng(3)
    nights = np.repeat(np.arange(12) * 1.0, 60) + np.tile(np.linspace(0, 0.3, 60), 12)  # 12 nights, 7 h each
    return nights + rng.uniform(0, 0.002, nights.size), rng


def test_lomb_scargle_finds_pulsation(sampling):
    t, rng = sampling
    p_true = 0.3141
    y = 0.05 * np.sin(2 * np.pi * t / p_true) + rng.normal(0, 0.01, t.size)
    _, _, best = lomb_scargle(t, y, p_min=0.1, p_max=2)
    assert abs(best - p_true) / p_true < 0.002


def test_bls_finds_transit(sampling):
    t, rng = sampling
    p_true, dur = 1.337, 0.08
    y = 1 - 0.01 * (np.abs(fold(t, p_true, 0.2)) * p_true < dur / 2) + rng.normal(0, 0.003, t.size)
    _, _, best = bls(t, y, p_min=0.5, p_max=4)
    assert abs(best - p_true) / p_true < 0.003


def test_pdm_finds_eclipsing_binary(sampling):
    t, rng = sampling
    p_true = 0.8123  # two unequal eclipses per period: Lomb-Scargle tends to pick P/2
    ph = fold(t, p_true)
    y = 1 - 0.3 * np.exp(-0.5 * (ph / 0.03) ** 2) - 0.15 * np.exp(-0.5 * ((np.abs(ph) - 0.5) / 0.03) ** 2)
    y += rng.normal(0, 0.005, t.size)
    _, _, best = pdm(t, y, p_min=0.3, p_max=2)
    assert abs(best - p_true) / p_true < 0.002


def test_fold_phase_zero_at_t0():
    assert fold([10.0, 10.5, 11.0], 1.0, t0=10.0).tolist() == [0.0, -0.5, 0.0]

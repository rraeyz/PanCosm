"""PER-9: the WWZ traces a drifting period and a mode switch."""

import time

import numpy as np
import pytest

from astrowb.timeseries import timefreq as tf


def test_a_chirp_is_traced():
    rng = np.random.default_rng(1)
    t = np.sort(rng.uniform(0, 4000, 1500))
    period = 300 + 30 * t / 4000  # 300 → 330 d
    phase = np.cumsum(np.r_[0, np.diff(t) / period[:-1]])
    x = np.sin(2 * np.pi * phase) + rng.normal(0, 0.2, t.size)
    freqs = np.linspace(1 / 360, 1 / 280, 200)
    taus = np.linspace(600, 3400, 30)
    z, amp, _ = tf.wwz(t, x, freqs, taus)
    got = 1 / tf.ridge(freqs, z)
    truth = 300 + 30 * taus / 4000
    assert np.max(np.abs(got / truth - 1)) < 0.02
    assert np.nanmedian(amp[np.nanargmax(z, axis=0), np.arange(len(taus))]) == pytest.approx(1.0, rel=0.1)


def test_a_mode_switch_and_gaps():
    rng = np.random.default_rng(2)
    t = np.sort(np.concatenate([rng.uniform(0, 100, 1500), rng.uniform(160, 260, 1500)]))
    x = np.where(t < 130, np.sin(2 * np.pi * 1.0 * t), np.sin(2 * np.pi * 1.3 * t)) + rng.normal(0, 0.3, t.size)
    freqs = np.linspace(0.8, 1.5, 141)
    taus = np.array([30.0, 70.0, 130.0, 190.0, 230.0])
    z, _amp, _ = tf.wwz(t, x, freqs, taus, c=0.002)  # about 3.6 cycles each side: sharper in frequency
    f = tf.ridge(freqs, z)
    assert f[0] == pytest.approx(1.0, abs=0.01) and f[-1] == pytest.approx(1.3, abs=0.01)
    assert np.isnan(f[2])  # inside the gap: too few effective points


def test_speed():
    rng = np.random.default_rng(3)
    t = np.sort(rng.uniform(0, 1000, 5000))
    x = np.sin(2 * np.pi * t / 37) + rng.normal(0, 0.5, t.size)
    began = time.perf_counter()
    tf.wwz(t, x, np.linspace(0.01, 0.1, 50), np.linspace(0, 1000, 200))
    assert time.perf_counter() - began < 30  # a quarter of the plan's grid; its 5 s for the whole is the native twin's

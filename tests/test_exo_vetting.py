"""EXO-11: a planet passes the vetting tests; an eclipsing binary at twice the period does not."""

import numpy as np

from astrowb.exoplanets import vetting
from astrowb.occult.model import transit


def curve(depths=(0.01, 0.01), secondary=0.0, ellipsoidal=0.0, seed=1):
    rng = np.random.default_rng(seed)
    t = np.arange(0, 27, 2 / 1440)
    p, t0 = 2.0, 0.7
    f = 1 - ellipsoidal * np.cos(4 * np.pi * (t - t0) / p)
    n = np.round((t - t0) / p)
    for parity, d in enumerate(depths):
        k = np.sqrt(d)
        model = transit(t, p, t0, k, 7.0, 89.0, "quadratic", (0.4, 0.2))
        f = np.where(n % 2 == parity, f * model, f)
    if secondary:
        f = f - secondary * (np.abs(((t - t0) / p - 0.5 + 0.5) % 1 - 0.5) * p < 0.05)
    err = np.full(t.size, 0.001)
    return t, f + rng.normal(0, 0.001, t.size), err, p, t0


def test_a_planet_is_green_and_binaries_are_not():
    t, f, err, p, t0 = curve()
    s = vetting.sheet(t, f, err, p, t0, 0.13, b=0.2, k=0.1)
    assert all(v["mark"] == "green" for v in s.values()), s
    t, f, err, p, t0 = curve(depths=(0.012, 0.007))  # primary and secondary of an EB folded at half its period
    assert vetting.odd_even(t, f, err, p, t0, 0.13)["mark"] == "red"
    t, f, err, p, t0 = curve(secondary=0.002, ellipsoidal=0.001)
    assert vetting.secondary(t, f, err, p, t0, 0.13)["mark"] == "red"
    assert vetting.sweet(t, f, err, p, t0, 0.13)["mark"] == "red"
    assert vetting.v_shape(0.95, 0.3)["mark"] == "red"

"""PER-4: aliases labelled, false-alarm probabilities that keep their promise, frequency errors that match."""

import numpy as np
from astropy.timeseries import LombScargle

from astrowb.timeseries import methods
from astrowb.timeseries import significance as sg

P = 0.3719


def nightly(rng, n=200, nights=40):
    return np.sort(rng.integers(0, nights, n) + 0.3 + rng.uniform(0, 0.3, n))


def test_the_daily_aliases_are_labelled_and_the_true_peak_ranked_first():
    first = 0
    for seed in range(20):
        rng = np.random.default_rng(seed)
        t = nightly(rng)
        y = 0.1 * np.sin(2 * np.pi * t / P) + rng.normal(0, 0.1, t.size)
        periods, power, _best = methods.gls(t, y, p_min=0.1, p_max=5)
        rows = sg.peak_table(periods, power, t)
        first += abs(rows[0]["period"] / P - 1) < 0.01
        if seed == 0:
            assert "alias by 1 d⁻¹ of peak 1" in [r["note"] for r in rows[1:3]]
    assert first >= 18  # ≥ 90 %


def test_the_analytic_one_percent_level_is_exceeded_one_percent_of_the_time():
    exceed = 0
    for seed in range(400):
        rng = np.random.default_rng(seed)
        t = np.sort(rng.uniform(0, 30, 150))
        y = rng.normal(0, 1, 150)
        f = np.linspace(1 / 15, 5, 4000)
        exceed += sg.fap_baluev(t, y, None, float(LombScargle(t, y).power(f).max()), 1 / 15, 5) < 0.01
    assert 0.0025 <= exceed / 400 <= 0.025


def test_shuffled_and_analytic_fap_agree_within_two():
    rng = np.random.default_rng(1)  # a peak at about the 1 % level
    t = np.sort(rng.uniform(0, 30, 150))
    y = 0.6 * np.sin(2 * np.pi * t / 1.7) + rng.normal(0, 1, 150)
    f = np.linspace(1 / 15, 5, 3000)

    def search(tt, yy):
        p = LombScargle(tt, yy).power(f)
        return 1 / f, p, 1 / f[int(np.argmax(p))]

    best = float(search(t, y)[1].max())
    analytic = sg.fap_baluev(t, y, None, best, 1 / 15, 5)
    shuffled = sg.fap_shuffled(t, y, search, best, n=400)
    assert 0.005 < analytic < 0.3 and 0.5 < shuffled / analytic < 2


def test_frequency_error_matches_the_scatter():
    f0, amp, noise = 1 / P, 0.05, 0.05
    found = []
    for seed in range(200):
        rng = np.random.default_rng(seed)
        t = np.sort(rng.uniform(0, 20, 300))
        y = amp * np.sin(2 * np.pi * f0 * t) + rng.normal(0, noise, t.size)
        f = np.linspace(f0 - 0.02, f0 + 0.02, 4001)
        found.append(f[int(np.argmax(LombScargle(t, y).power(f)))])
    expected = sg.frequency_error(np.linspace(0, 20, 300), amp, noise)
    assert 0.8 < np.std(found) / expected < 1.2

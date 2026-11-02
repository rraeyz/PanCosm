"""PER-12: the recovery map and the analytic 50 % level of the Lomb–Scargle search."""

import numpy as np
import pytest
from astropy.timeseries import LombScargle

from astrowb.timeseries import injection as inj


@pytest.mark.slow
def test_the_50_percent_level_follows_the_analytic_one():
    rng = np.random.default_rng(1)
    t = np.sort(rng.uniform(0, 50, 1000))
    noise = rng.normal(0, 1.0, t.size)
    freqs = np.linspace(0.02, 5, 20000)

    def search(tt, y):
        return 1 / freqs[np.argmax(LombScargle(tt, y).power(freqs))]

    amps = np.linspace(0.05, 0.3, 11)
    frac = inj.recovery(t, noise, [0.7, 1.9], amps, search, n=30)
    expected = inj.gls_half_amplitude(t.size, 1.0, 50, 5)
    for row in frac:
        a50 = np.interp(0.5, np.maximum.accumulate(row), amps)  # the fraction grows with the amplitude
        assert a50 == pytest.approx(expected, rel=0.2)


def test_aliases_count_for_eclipses_and_the_map_is_ordered():
    t = np.linspace(0, 30, 600)
    base = np.random.default_rng(2).normal(0, 0.1, t.size)

    def search(_t, _y):
        return 1.0  # a search that always finds half the injected 2-day period

    frac = inj.recovery(t, base, [2.0], [0.5], search, n=4)
    assert frac[0, 0] == 0
    assert inj.recovery(t, base, [2.0], [0.5], search, n=4, aliases=True)[0, 0] == 1

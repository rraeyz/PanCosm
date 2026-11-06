import numpy as np
import pytest

from astrowb.timeseries import fourier


@pytest.fixture
def sampling():
    """Eight nights of 6 h with gaps: the daily aliases a real ground-based run has."""
    rng = np.random.default_rng(7)
    t = np.concatenate([n + np.sort(rng.uniform(0, 0.25, 150)) for n in range(8)])
    return t, rng


def test_dft_amplitude_and_window(sampling):
    t, rng = sampling
    y = 0.03 * np.sin(2 * np.pi * 7.3 * t) + rng.normal(0, 0.002, t.size)
    f = fourier.default_grid(t, 20)
    a = fourier.dft(t, y, f)
    assert abs(f[np.argmax(a)] - 7.3) < 0.02
    assert abs(a.max() - 0.03) < 0.003
    w = fourier.spectral_window(t, np.array([1e-6, 1.0, 0.5]))
    assert w[0] > 0.999 and w[1] > 0.8 > w[2]  # one-day alias from the nightly gaps


def test_prewhitening_recovers_three_frequencies(sampling):
    t, rng = sampling
    truth = [(9.1234, 0.020, 0.1), (11.876, 0.010, 0.6), (4.321, 0.005, 0.3)]
    y = 1 + sum(a * np.sin(2 * np.pi * (f * (t - t.min()) + p)) for f, a, p in truth)
    y += rng.normal(0, 0.002, t.size)
    fit, *_, snr = fourier.prewhiten(t, y, f_max=25)
    assert fit is not None and len(fit["freq"]) == 3 and np.all(snr >= 4)
    order = np.argsort(-fit["amp"])
    for k, (f, a, p) in zip(order, truth, strict=True):
        assert abs(fit["freq"][k] - f) < 4 * fit["freq_err"][k] + 1e-4
        assert abs(fit["amp"][k] - a) < 4 * fit["amp_err"][k]
        dp = (fit["phase"][k] - p + 0.5) % 1 - 0.5
        assert abs(dp) < 4 * fit["phase_err"][k] + 0.01
    assert abs(fit["rms"] - 0.002) < 0.0003
    assert np.allclose(fourier.evaluate(fit, t), y, atol=0.01)


def test_prewhitening_stops_on_noise():
    rng = np.random.default_rng(1)
    t = np.sort(rng.uniform(0, 10, 500))
    fit, *_ = fourier.prewhiten(t, rng.normal(0, 0.01, t.size), f_max=20)
    assert fit is None


def test_anova_finds_non_sinusoidal_period(sampling):
    t, rng = sampling
    p = 0.3712  # RR Lyrae-like sawtooth: steep rise, slow decline
    ph = (t / p) % 1
    y = np.where(ph < 0.15, ph / 0.15, (1 - ph) / 0.85) * 0.5 + rng.normal(0, 0.01, t.size)
    _, theta, best = fourier.anova(t, y, p_min=0.1, p_max=2, n_harmonics=3)
    assert abs(best - p) / p < 0.002 and theta.max() > 100


def test_times_of_maximum(sampling):
    t, rng = sampling
    f0, phi = 3.7, 0.2
    y = 0.1 * np.sin(2 * np.pi * (f0 * t + phi)) + rng.normal(0, 0.003, t.size)
    fit = fourier.fourier_fit(t, y, [3.69])
    maxima = fourier.times_of_maximum(t, y, fit)
    assert len(maxima) >= 5
    for tm, err in maxima:
        k = np.round(f0 * tm + phi - 0.25)
        true = (k + 0.25 - phi) / f0
        assert abs(tm - true) < max(5 * err, 0.003)
    mags = fourier.times_of_maximum(t, -y, fourier.fourier_fit(t, -y, [3.69]), magnitudes=True)
    assert np.allclose([m[0] for m in mags], [m[0] for m in maxima])


def test_phase_binning_and_editing():
    ph = np.linspace(-0.5, 0.4999, 1000)
    c, mean, err, n = fourier.bin_phase(ph, np.cos(2 * np.pi * ph), 20)
    assert len(c) == 20 and n.sum() == 1000 and np.allclose(mean, np.cos(2 * np.pi * c), atol=0.02)
    y = np.r_[np.zeros(99), 50.0]
    assert fourier.sigma_clip(y + np.random.default_rng(0).normal(0, 1, 100)).sum() == 99
    t = np.linspace(0, 3, 3000)  # an eclipsing binary: the eclipses are signal, only the spike goes
    y = 1 - 0.4 * np.exp(-0.5 * (((t % 0.8) - 0.4) / 0.02) ** 2) + np.random.default_rng(1).normal(0, 0.005, t.size)
    y[17] = 1.3
    keep = fourier.sigma_clip(y, 4, t, 0.8)  # in phase
    assert not keep[17] and keep.sum() >= 2990
    keep = fourier.sigma_clip(y, 4, t)  # in time: a slope or a well-sampled eclipse is not clipped either
    assert not keep[17] and keep.sum() >= 2985
    y = 0.1 * np.r_[np.arange(8.0), 80, 9, 10, 11, 12, 13, 14] + np.random.default_rng(0).normal(0, 0.1, 15)
    keep = fourier.sigma_clip(y, 4, np.r_[np.arange(8), np.arange(100, 107)])  # an outlier opening a night
    assert keep.tolist() == [True] * 8 + [False] + [True] * 6
    tb, yb = fourier.bin_time(np.arange(10.0), np.arange(10.0), 5)
    assert tb.tolist() == [2.0, 7.0] and yb.tolist() == [2.0, 7.0]
    assert np.allclose(fourier.mag_to_flux(fourier.flux_to_mag([0.5, 2])), [0.5, 2])


def test_clean_removes_the_daily_aliases(sampling):
    t, rng = sampling
    y = 0.03 * np.sin(2 * np.pi * 7.3 * t) + 0.012 * np.sin(2 * np.pi * 11.17 * t + 1) + rng.normal(0, 0.002, t.size)
    f, amp, comps = fourier.clean(t, y, f_max=20)
    dirty = fourier.dft(t, y, f)
    near = lambda arr, f0: arr[np.abs(f - f0) < 0.05].max()  # noqa: E731
    assert abs(near(amp, 7.3) - 0.03) < 0.003 and abs(near(amp, 11.17) - 0.012) < 0.003
    for alias in (6.3, 8.3):  # one-day aliases of 7.3 c/d: strong in the raw spectrum, gone after CLEAN
        assert near(dirty, alias) > 0.5 * near(dirty, 7.3)
        assert near(amp, alias) < 0.15 * near(amp, 7.3)
    assert abs(comps[0][0] - 7.3) < 0.02 and abs(comps[0][1] - 0.03) < 0.01


def test_fast_spectrum_equals_the_direct_sum():
    """The block-factorised transform (PLAN 4.8 item 12) gives the direct sum of every cos / sin to rounding."""
    from astrowb.timeseries import fourier

    rng = np.random.default_rng(5)
    t = np.sort(rng.uniform(0, 27.3, 4000)) + 2460000.0  # a TESS sector in BJD: large absolute times
    y = 0.01 * np.sin(2 * np.pi * 7.123 * t) + rng.normal(0, 0.002, t.size)
    grid = fourier.default_grid(t, 50.0)
    tt, yy = t - t.min(), y - y.mean()
    direct = np.empty(grid.size, complex)
    for i in range(0, grid.size, 200):
        direct[i : i + 200] = np.exp(-2j * np.pi * np.outer(grid[i : i + 200], tt)) @ yy
    fast = fourier._exp_sums(tt, yy, grid)
    assert np.max(np.abs(fast - direct)) < 1e-9 * np.max(np.abs(direct))
    assert np.allclose(fourier.dft(t, y, grid), 2 * np.abs(direct) / t.size, rtol=0, atol=1e-12)
    win = fourier.spectral_window(t, grid)
    assert np.allclose(win, np.abs(np.exp(-2j * np.pi * np.outer(grid, tt)).sum(1)) / t.size, rtol=0, atol=1e-12)
    uneven = np.sort(rng.uniform(1, 40, 3000))  # an uneven grid takes the direct path
    ref = np.abs(np.exp(-2j * np.pi * np.outer(uneven, tt)) @ yy)
    assert np.allclose(np.abs(fourier._exp_sums(tt, yy, uneven)), ref, rtol=1e-12, atol=1e-12)


def test_binned_errors_and_a_weighted_period_search():
    from astrowb.engine.steps import execute
    from astrowb.timeseries.fourier import bin_time

    t = np.repeat(np.arange(10), 10) * 0.1 + np.tile(np.arange(10), 10) * 0.005  # ten points in each 0.1 bin
    y = np.ones_like(t)
    tb, yb, eb = bin_time(t, y, 0.1, np.full(t.size, 0.02))
    assert np.allclose(eb, 0.02 / np.sqrt(10))  # ten points of 0.02 per bin

    class Ctx:
        def progress(self, *a):
            pass

    rng = np.random.default_rng(2)
    t = np.sort(rng.uniform(0, 20, 600))
    e = np.where(rng.uniform(size=t.size) < 0.3, 0.2, 0.01)  # a third of the points far noisier
    f = 1 + 0.03 * np.sin(2 * np.pi * t / 1.37) + rng.normal(0, e)
    out = execute("timeseries.period", {"time": t, "flux": f, "err": e}, {"p_min": 0.3, "p_max": 5.0}, Ctx())
    assert abs(out["best"] - 1.37) < 0.005

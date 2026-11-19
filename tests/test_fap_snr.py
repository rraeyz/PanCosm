"""FAP (Baluev 2008) and S/N (Breger 1993) of the frequencies step, and their table columns (UI-16.4)."""

import numpy as np
from PySide6.QtCore import Qt

from astrowb.timeseries import fourier, significance
from astrowb.ui.frequency_page import FrequencyPage


def _times():
    return np.sort(np.random.default_rng(1).uniform(0, 30, 600))


def test_fap_is_tiny_for_a_sinusoid_and_large_for_noise():
    t, rng = _times(), np.random.default_rng(2)
    y = 0.1 * np.sin(2 * np.pi * 3.7 * t) + rng.normal(0, 0.05, t.size)
    assert significance.frequency_faps(t, y, [3.7], 10)[0] < 1e-10
    noise = rng.normal(0, 0.05, t.size)
    freqs = np.linspace(0.05, 10, 4000)
    from astropy.timeseries import LombScargle

    best = freqs[np.argmax(LombScargle(t, noise).power(freqs))]
    assert significance.frequency_faps(t, noise, [best], 10)[0] > 0.01


def test_snr_is_amplitude_over_the_mean_residual_amplitude():
    t, rng = _times(), np.random.default_rng(3)
    y = 0.1 * np.sin(2 * np.pi * 3.7 * t) + rng.normal(0, 0.05, t.size)
    fit, grid, _first, resid, snr = fourier.prewhiten(t, y, 10, n_max=1)
    # white noise sigma s gives a mean amplitude of sqrt(pi / N) s (Rayleigh); accept 25 %
    expected = fit["amp"][0] / (np.sqrt(np.pi / t.size) * 0.05)
    assert abs(snr[0] - expected) / expected < 0.25 and abs(fit["freq"][0] - 3.7) < 0.01


def test_table_has_fap_and_marks_a_low_snr(qtbot):
    class Page:
        time, flux = [], []

    page = FrequencyPage(Page())
    qtbot.addWidget(page)
    row = {"freq": 2.0, "freq_err": 0.01, "amp": 1.0, "amp_err": 0.1, "phase": 0.1, "phase_err": 0.01}
    out = {"frequencies": [row | {"snr": 12.0, "fap": 1e-9}, row | {"freq": 3.0, "snr": 2.5, "fap": 0.4}],
           "maxima": [], "rms": 0.1, "grid": [1.0, 2.0], "spectrum": [0, 1], "residual_spectrum": [0, 1],
           "window": [1, 0]}  # fmt: skip
    page.show_result(out)
    model = page.table.model
    assert model.table.colnames[-2] == "FAP" and model.table["FAP"][1] == 0.4
    snr = model.table.colnames.index("S/N")
    assert model.data(model.index(0, snr), Qt.BackgroundRole) is None
    assert "Breger" in model.data(model.index(1, snr), Qt.ToolTipRole)


def _period_step(t, y):
    from astrowb.photometry.steps import period_step

    class Ctx:
        def progress(self, *a):
            pass

    return period_step(
        {"time": t.tolist(), "flux": y.tolist()}, {"method": "lomb-scargle", "p_min": 0.1, "p_max": None}, Ctx()
    )


def test_period_step_gives_the_peak_snr_and_fap():
    t, rng = _times(), np.random.default_rng(4)
    out = _period_step(t, 0.1 * np.sin(2 * np.pi * 3.7 * t) + rng.normal(0, 0.05, t.size))
    assert out["peak_snr"][0] > 4 and out["peak_faps"][0] < 1e-3
    assert len(out["peak_snr"]) == len(out["peak_faps"])
    noise = _period_step(t, rng.normal(0, 0.05, t.size))
    assert noise["peak_snr"][0] < 4


def test_peak_table_shows_snr_and_marks_the_weak_ones():
    from astrowb.ui.lightcurve_fold import peak_marks, peak_table

    periods = np.linspace(0.1, 5, 400)
    power = np.exp(-(((periods - 1) / 0.02) ** 2)) + 0.5 * np.exp(-(((periods - 2) / 0.02) ** 2))
    table = peak_table(
        {"periods": periods.tolist(), "power": power.tolist(), "peak_faps": [1e-5, 0.4], "peak_snr": [6.2, 2.0]}
    )
    assert table.colnames == ["period", "power", "fap", "snr"] and list(table["snr"]) == ["6.2", "2.0"]
    assert list(peak_marks(table)) == [(1, "snr")]
    assert list(peak_table({"periods": periods.tolist(), "power": power.tolist()})["snr"]) == ["—", "—"]

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
    assert model.table.colnames[-1] == "FAP" and model.table["FAP"][1] == 0.4
    snr = model.table.colnames.index("S/N")
    assert model.data(model.index(0, snr), Qt.BackgroundRole) is None
    assert "Breger" in model.data(model.index(1, snr), Qt.ToolTipRole)

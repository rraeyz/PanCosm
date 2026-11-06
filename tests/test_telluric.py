"""Telluric correction on a simulation with known atmosphere, airmass ratio and wavelength shift."""

import numpy as np
import pytest

from astrowb.spectroscopy import telluric

C = 299792.458
WAVE = np.exp(np.arange(np.log(6500), np.log(7800), 4.0 / C))  # 4 km/s pixels
RNG = np.random.default_rng(9)
T_LINES = np.concatenate([RNG.uniform(6860, 6950, 40), RNG.uniform(7160, 7340, 60), RNG.uniform(7590, 7700, 50)])
T_DEPTH = RNG.uniform(0.05, 0.5, len(T_LINES))  # optical depths at airmass 1
STAR_LINES = [6562.8, 6678.2, 7065.2, 7281.4, 7774.0]


def tau(wave, v=0.0):
    out = np.zeros_like(wave)
    for lam, d in zip(T_LINES, T_DEPTH, strict=True):
        out += d * np.exp(-0.5 * ((wave - lam * (1 + v / C)) / 0.15) ** 2)
    return out


def star(wave):
    f = np.ones_like(wave)
    for lam in STAR_LINES:
        f -= 0.4 * np.exp(-0.5 * ((wave - lam) / 1.5) ** 2)
    return f


def test_correction_recovers_the_star():
    continuum = 1000 * (1 + 0.2 * (WAVE - 7000) / 1000)
    sci_true = continuum * star(WAVE)
    sci = sci_true * np.exp(-1.4 * tau(WAVE, v=1.2))  # higher airmass, wavelength scale off by 0.3 px
    sci += RNG.normal(0, 3, len(WAVE))
    std = 5000 * (1 - 0.1 * (WAVE - 7000) / 1000) * np.exp(-1.0 * tau(WAVE)) + RNG.normal(0, 10, len(WAVE))
    r = telluric.correct(WAVE, sci, WAVE, std)
    assert r["power"] == pytest.approx(1.4, abs=0.05)
    assert r["shift_kms"] == pytest.approx(1.2, abs=0.4)
    good = ~r["bad"]
    before = np.std((sci / sci_true)[good])
    after = np.std((r["flux"] / sci_true)[good])
    assert after < 0.25 * before and after < 0.01
    # the stellar lines are kept (only the atmosphere is divided out)
    halpha = np.argmin(np.abs(WAVE - 6562.8))
    assert r["flux"][halpha] / continuum[halpha] == pytest.approx(0.6, abs=0.02)


def test_refuses_without_telluric_bands():
    w = np.linspace(4000, 4500, 2000)
    with pytest.raises(ValueError):
        telluric.correct(w, np.ones_like(w), w, np.ones_like(w))


def test_telluric_step_and_tab(tmp_path, qtbot):
    from astrowb.engine.steps import execute
    from astrowb.spectroscopy import spectrum_io
    from astrowb.ui.spectro_page import TelluricTab

    sci = 1000 * star(WAVE) * np.exp(-1.2 * tau(WAVE))
    spectrum_io.write(tmp_path / "sci.fits", WAVE, sci, np.full(len(WAVE), 3.0))
    spectrum_io.write(tmp_path / "std.fits", WAVE, 3000 * np.exp(-tau(WAVE)), np.full(len(WAVE), 5.0))

    class Ctx:
        def progress(self, *a):
            pass

    out = execute(
        "spectroscopy.telluric",
        {
            "spectrum": str(tmp_path / "sci.fits"),
            "standard": str(tmp_path / "std.fits"),
            "output": str(tmp_path / "c.fits"),
        },
        {},
        Ctx(),
    )["telluric"]
    w, f, e, h = spectrum_io.read(out["path"])
    ok = np.isfinite(f)
    assert h["TELLPOW"] == pytest.approx(1.2, abs=0.03) and np.std((f / (1000 * star(w)))[ok]) < 0.005
    assert np.all(e[ok] >= 3.0)  # errors grow where light was absorbed
    # the plotted spectrum is the saved one: saturated cores left out (they spiked to ±10 on a real FEROS tau Ceti)
    assert np.array_equal(np.isnan(np.asarray(out["corrected"], float)), ~ok)
    tab = TelluricTab()
    qtbot.addWidget(tab)
    tab.show_result(out)
    assert "1.2" in tab.status.text()

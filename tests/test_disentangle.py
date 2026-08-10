"""Disentangling: both stars' spectra recovered from simulated composites with known velocities."""

from pathlib import Path

import numpy as np
import pytest
from test_sb2 import DEPTH1, DEPTH2, LINES1, LINES2, WAVE, template

from astrowb.spectroscopy import disentangle as disentangle_module
from astrowb.spectroscopy.disentangle import disentangle


def test_both_spectra_are_recovered():
    rng = np.random.default_rng(5)
    ratio = 0.5
    phases = np.linspace(0, 1, 14, endpoint=False)
    v1, v2 = 60 * np.sin(2 * np.pi * phases) + 5, -90 * np.sin(2 * np.pi * phases) + 5
    fluxes = [
        (template(LINES1, DEPTH1, 0.08, a) + ratio * template(LINES2, DEPTH2, 0.20, b)) / (1 + ratio)
        + rng.normal(0, 0.003, len(WAVE))
        for a, b in zip(v1, v2, strict=True)
    ]
    w, s1, s2 = disentangle([WAVE] * len(fluxes), fluxes, v1, v2, light_ratio=ratio)
    true1, true2 = template(LINES1, DEPTH1, 0.08, 0.0, w), template(LINES2, DEPTH2, 0.20, 0.0, w)
    assert np.std(s1 - true1) < 0.01 and np.std(s2 - true2) < 0.02  # line depths up to 0.6
    assert np.corrcoef(s2, true2)[0, 1] > 0.98 and np.corrcoef(s2, true1)[0, 1] < 0.3  # no leak of star 1


def test_spikes_and_gaps_stay_out_of_the_components():
    """Cosmic rays / pipeline spikes and NaN (a telluric-corrected spectrum's band cores) in single spectra."""
    rng = np.random.default_rng(7)
    phases = np.linspace(0, 1, 10, endpoint=False)
    v1, v2 = 60 * np.sin(2 * np.pi * phases), -90 * np.sin(2 * np.pi * phases)
    fluxes = []
    for a, b in zip(v1, v2, strict=True):
        f = (template(LINES1, DEPTH1, 0.08, a) + 0.5 * template(LINES2, DEPTH2, 0.20, b)) / 1.5
        f = f + rng.normal(0, 0.003, len(WAVE))
        f[rng.choice(len(WAVE), 15, replace=False)] += rng.uniform(0.3, 1.5, 15)
        f[rng.integers(0, len(WAVE) - 20) + np.arange(20)] = np.nan
        fluxes.append(f)
    w, s1, s2 = disentangle([WAVE] * len(fluxes), fluxes, v1, v2, light_ratio=0.5)
    true1, true2 = template(LINES1, DEPTH1, 0.08, 0.0, w), template(LINES2, DEPTH2, 0.20, 0.0, w)
    assert np.all(np.isfinite(s1)) and np.all(np.isfinite(s2))
    assert np.max(np.abs(s1 - true1)) < 0.05 and np.max(np.abs(s2 - true2)) < 0.1  # no spike carried over
    assert disentangle_module.separable_width(v1, v2) == pytest.approx(2 * 150 * np.sin(2 * np.pi * 0.2), rel=1e-6)


def test_step_and_velocity_tab(qtbot, tmp_path):
    from test_sb2 import composite

    from astrowb.engine.steps import execute
    from astrowb.spectroscopy import spectrum_io
    from astrowb.ui.spectro_page import VelocityTab

    class Ctx:
        def progress(self, *a):
            pass

    rows, paths = [], []
    for i, ph in enumerate(np.linspace(0, 1, 8, endpoint=False)):
        a, b = 60 * np.sin(2 * np.pi * ph), -90 * np.sin(2 * np.pi * ph)
        p = spectrum_io.write(tmp_path / f"s{i}.fits", WAVE, composite(a, b), np.full(len(WAVE), 0.01))
        paths.append(str(p))
        rows.append(
            {
                "file": Path(p).name,
                "bjd": 2461000.0 + i,
                "rv": None,
                "rv_obs": a,
                "rv_err": 0.5,
                "rv2_obs": b,
                "rv2_err": 1.0,
                "rv2": None,
                "flux_ratio": 0.5,
                "v_corr": None,
            }
        )
    tab = VelocityTab()
    qtbot.addWidget(tab)
    tab.files.addItems(paths)
    tab.show_rvs(rows)
    assert tab.separate_button.isEnabled()
    sent = []
    tab.disentangle_requested.connect(lambda i, p: sent.append((i, p)))
    tab.separate(str(tmp_path / "out"))
    inputs, params = sent[0]
    assert inputs["light_ratio"] == 0.5 and inputs["rv2"][2] == rows[2]["rv2_obs"]
    c = execute("spectroscopy.disentangle", inputs, params, Ctx())["components"]
    assert all(np.isfinite(c["star1"])) and len(c["paths"]) == 2
    tab.show_components(c)
    assert "star2.fits" in tab.status.text() and "changes by 300 km/s" in tab.status.text()

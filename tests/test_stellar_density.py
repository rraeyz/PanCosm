"""UI-16.7: stellar density from a transit fit."""

import numpy as np
import pytest

from astrowb.photometry.stellar_density import stellar_density
from astrowb.ui.exoplanets_density import density_line


def fit(a=215.03, ea=2.0, chains=None):
    out = {"values": {"a_rs": a}, "errors": {"a_rs": ea}}
    if chains is not None:
        out["mcmc"] = {"names": ["k", "a_rs"], "chains": chains}
    return out


def test_sun_earth_density():
    d = stellar_density(fit(), 365.25)
    assert d["rho"] == pytest.approx(1.41, rel=0.01)
    assert d["rho_sun"] == pytest.approx(1.0, rel=0.01)


def test_error_propagation_matches_samples():
    rng = np.random.default_rng(1)
    a = rng.normal(215.03, 2.0, 20000)
    ch = np.stack([np.zeros_like(a), a], axis=1).reshape(4, 5000, 2).tolist()
    lin = stellar_density(fit(), 365.25)["err"]
    mc = stellar_density(fit(chains=ch), 365.25)["err"]
    assert mc == pytest.approx(lin, rel=0.05)
    assert stellar_density(fit(), 365.25, 1.0)["err"] > lin


def test_line_with_expected(qapp):
    text = density_line(fit(), 365.25, 1.30)
    assert "Stellar density: 1.41 ± 0.04 g/cm³ (1.00 ρ☉)" in text and "σ from the expected 1.30" in text
    assert "σ" not in density_line(fit(), 365.25)


def test_window_shows_the_density_line(qtbot, tmp_path):
    from astrowb.occult.model import transit
    from astrowb.photometry import lcfile
    from astrowb.settings import Settings
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    t = np.linspace(-0.12, 0.12, 265) + 2459500.6123
    f = transit(t - 2459500.6123, 1.42, 0.0, 0.145, 6.3, np.degrees(np.arccos(0.5 / 6.3)), "quadratic", (0.4, 0.2))
    lc = {"time": t.tolist(), "rel_flux": f.tolist(), "rel_flux_err": [0.0015] * t.size, "time_scale": "BJD_TDB"}
    lcfile.write(lc, tmp_path / "n.lc.ecsv")
    win.open_area("exoplanets")
    page = win.exoplanets_page
    page.add_files([str(tmp_path / "n.lc.ecsv")])
    page.period.setValue(1.42)
    page.detrend.setText("")
    page.fit_button.click()
    qtbot.waitUntil(lambda: 0 in page.fits, timeout=60000)
    assert "Stellar density: " in page.result.text() and "from the expected" not in page.result.text()
    page.expected_rho.setValue(1.0)
    assert "σ from the expected 1.00" in page.result.text()
    win.engine.shutdown()

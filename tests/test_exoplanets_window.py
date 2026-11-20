"""UI-16.7: the Exoplanets window fits a transit on a saved light-curve file."""

import numpy as np
import pytest

from astrowb.occult.model import transit
from astrowb.photometry import lcfile
from astrowb.settings import Settings

P, TC, K, A, B = 1.42, 2459500.6123, 0.145, 6.3, 0.5


@pytest.fixture
def window(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    yield win
    win.engine.shutdown()


def test_the_exoplanets_window_has_stages(window):
    win = window.open_area("exoplanets")
    page = window.exoplanets_page
    assert list(win.stage_panels) == ["data", "star", "planets", "model", "fit", "uncertainty", "results"]
    panels = win.stage_panels
    assert panels["data"].isAncestorOf(page.table) and panels["star"].isAncestorOf(page.u1)
    assert panels["planets"].isAncestorOf(page.period) and panels["model"].isAncestorOf(page.detrend)
    assert panels["fit"].isAncestorOf(page.fit_button) and panels["uncertainty"].isAncestorOf(page.mcmc)
    assert panels["results"].isAncestorOf(page.etd_button)
    assert not any(p.isAncestorOf(page.plot) for p in panels.values())
    win.close()


def test_a_transit_in_a_light_curve_file_is_fitted_in_the_window(window, qtbot, tmp_path):
    rng = np.random.default_rng(3)
    t = np.linspace(TC - 0.12, TC + 0.12, 265)
    f = transit(t - TC, P, 0.0, K, A, np.degrees(np.arccos(B / A)), "quadratic", (0.4, 0.2))
    lc = {"time": t.tolist(), "rel_flux": (f + rng.normal(0, 0.0015, t.size)).tolist(),
          "rel_flux_err": [0.0015] * t.size, "time_scale": "BJD_TDB"}  # fmt: skip
    path = tmp_path / "night.lc.ecsv"
    lcfile.write(lc, path)
    win = window.open_area("exoplanets")
    page = window.exoplanets_page
    page.add_files([str(path)])
    assert win.rail.states["data"] == "done" and page.table.table.rowCount() == 1
    page.period.setValue(P)
    page.detrend.setText("")
    page.fit_button.click()
    qtbot.waitUntil(lambda: 0 in page.fits, timeout=60000)
    fit = page.fits[0]
    assert fit["values"]["tc"] == pytest.approx(TC, abs=4 * fit["errors"]["tc"] + 1e-4)
    assert fit["values"]["k"] == pytest.approx(K, abs=0.02)
    assert page.values.table.rowCount() > 8 and page.result.text().startswith("Mid-transit")
    assert win.rail.states["results"] == "done"
    for kind, name in (("exoclock", "ExoClock.txt"), ("etd", "ETD.txt")):
        assert page.export(kind, str(tmp_path / name)) and (tmp_path / name).stat().st_size > 0
    (tmp_path / "bad.txt").write_text("1 2\n" * 20)
    page.add_files([str(tmp_path / "bad.txt")])  # not time, flux, error: said, not a crash
    assert page.table.table.rowCount() == 1 and "Cannot read" in page.result.text()
    win.close()

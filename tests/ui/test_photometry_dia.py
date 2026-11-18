"""PHO-29: the Photometry window's "Difference imaging (crowded field)…" action and its result tab."""

import numpy as np
import pytest
from astropy.io import fits
from test_dia import render

from astrowb.settings import Settings


@pytest.fixture
def window(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    win.show_workspace("photometry")
    yield win
    win.engine.shutdown()


def _frames(tmp_path, n=6, blank=False):
    rng = np.random.default_rng(3)
    xy = rng.uniform(12, 88, (60, 2))
    flux = 10 ** rng.uniform(3.0, 4.5, 60)
    flux[0], xy[0] = 3e4, (50.0, 50.0)
    amps = 1 + 0.08 * np.sin(np.arange(n))
    paths = []
    for k in range(n):
        f = flux.copy()
        f[0] *= amps[k]
        img = rng.normal(300, 5, (100, 100)) if blank else render(xy, f, 1.2 + 0.05 * k, (100, 100), 300.0, rng)
        p = tmp_path / f"f{k}.fits"
        header = fits.Header({"EXPTIME": 30.0, "DATE-OBS": f"2026-11-15T20:{k * 2:02d}:00"})
        fits.PrimaryHDU(img.astype(np.float32), header).writeto(p)
        paths.append(str(p))
    return paths, amps, xy[0], flux[0]


def _page(window, paths, target):
    page = window.photometry_page
    page.images, page.target = paths, (float(target[0]), float(target[1]))
    return page


def test_flux_changes_in_a_result_tab(window, qtbot, tmp_path):
    paths, amps, xy, f0 = _frames(tmp_path)
    page = _page(window, paths, xy)
    page._dia_fwhm = 2.3548 * 1.2
    page.dia_button.click()
    qtbot.waitUntil(lambda: hasattr(page, "dia_tab"), timeout=60000)
    assert "relative to the reference" in page.dia_tab.note.text()
    assert page.dia_frames.value() == 5  # min(5, 6)
    series = page.dia_tab.plot.figure.panels[0].series[0]
    truth = (amps - amps[:5].mean()) * f0  # the reference holds the mean of the sharpest frames
    assert np.all(np.abs(np.asarray(series.y) - truth) < 4 * np.asarray(series.yerr) + 0.05 * f0)


def test_every_failure_is_said(window, qtbot, tmp_path):
    paths, _, xy, _ = _frames(tmp_path, n=3, blank=True)
    page = window.photometry_page
    page.dia_button.click()
    assert "Choose the images" in page.dia_note.text()
    _page(window, paths[:1], xy)
    page.dia_button.click()
    assert "at least two frames" in page.dia_note.text()
    _page(window, paths, xy)
    page.dia_button.click()
    assert "FWHM" in page.dia_note.text()
    page._dia_fwhm = 3.0
    page.dia_button.click()  # frames without a measurable star: the engine's AppError, shown not raised
    qtbot.waitUntil(lambda: "n_best" in page.dia_note.text() or "measurable" in page.dia_note.text(), timeout=30000)
    assert not hasattr(page, "dia_tab")

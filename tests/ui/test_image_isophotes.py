"""PHO-39: the Analyse tools for extended objects: the Isophotes tab and the sky brightness."""

import numpy as np
import pytest
from astropy.io import fits

from astrowb.settings import Settings
from astrowb.ui.image_isophotes import run_isophotes, sky_text
from astrowb.ui.main_window import MainWindow


def _galaxy(path, zp=None):
    rng = np.random.default_rng(1)
    yy, xx = np.mgrid[:200, :200]
    r = np.hypot(xx - 100, (yy - 100) / 0.8)
    img = rng.normal(50, 1, (200, 200)) + 2000 * np.exp(-r / 15)
    hdu = fits.PrimaryHDU(img.astype("float32"))
    if zp is not None:
        hdu.header["MAGZP"] = zp
    hdu.writeto(path)
    return str(path)


def _open(qtbot, tmp_path, zp=None):
    win = MainWindow(Settings(tmp_path / "cfg"))
    qtbot.addWidget(win)
    win.open_many([_galaxy(tmp_path / "g.fits", zp)])
    return win, win.image_page, win.area_windows["image"]


def test_isophote_profile_tab_with_surface_brightness(qtbot, tmp_path):
    win, page, iwin = _open(qtbot, tmp_path)
    run_isophotes(iwin, page, 100, 100, 25.0, 0.5)
    qtbot.waitUntil(lambda: getattr(page, "isophotes", None) is not None, timeout=20000)
    t = page.isophotes
    assert "surface_brightness" in t.colnames and "result_isophotes" in iwin.docks
    assert t["intensity"][0] > t["intensity"][-1] and t["sma"][0] < t["sma"][-1]
    win.engine.shutdown()


def test_sky_brightness_needs_zero_point_and_scale(qtbot, tmp_path):
    win, page, _ = _open(qtbot, tmp_path, zp=25.0)
    with pytest.raises(ValueError, match="pixel scale"):
        sky_text(page, 25.0, None)  # the file has no WCS: nothing is guessed
    with pytest.raises(ValueError, match="zero point"):
        sky_text(page, None, 1.0)
    expected = 25.0 - 2.5 * np.log10(50 / 1.0)
    assert abs(float(sky_text(page, 25.0, 1.0).split()[1]) - expected) < 0.15  # the galaxy's halo lifts the median
    win.engine.shutdown()

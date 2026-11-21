"""UI-16.10: every Star / Area / Line measurement is a row of the Measurements result tab."""

import numpy as np
from astropy.io import fits

from astrowb.settings import Settings
from astrowb.ui.main_window import MainWindow


def _star_fits(path):
    yy, xx = np.mgrid[:60, :60]
    img = 100 + 5000 * np.exp(-((xx - 30) ** 2 + (yy - 30) ** 2) / (2 * 2.0**2))
    img += np.random.default_rng(3).normal(0, 3, img.shape)
    fits.PrimaryHDU(img.astype("float32")).writeto(path)
    return str(path)


def test_star_and_area_measurements_become_rows(qtbot, tmp_path):
    win = MainWindow(Settings(tmp_path / "cfg"))
    qtbot.addWidget(win)
    win.open_many([_star_fits(tmp_path / "s.fits")])
    page = win.image_page
    assert page.measure_star(30, 30) is not None
    assert page.measure_area(10, 10, 20, 20) is not None
    m = page.measurement_table
    assert [r["tool"] for r in m.rows] == ["Star", "Area"]
    t = m.table.model.table
    assert len(t) == 2 and list(t["file"]) == ["s.fits", "s.fits"]
    assert t["fwhm"][0] > 0 and np.isnan(t["fwhm"][1])  # blank where a value does not apply
    assert t["pixels"][1] == 121 and np.isnan(t["sum"][0]) is np.True_
    m.delete([0])
    assert [r["tool"] for r in m.rows] == ["Area"]
    win.engine.shutdown()

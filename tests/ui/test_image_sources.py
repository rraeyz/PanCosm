"""UI-16.10: the Sources result tab lists the detected stars; a row click centres and marks the star."""

import numpy as np
from astropy.io import fits

from astrowb.settings import Settings
from astrowb.ui.image_sources import find_stars
from astrowb.ui.main_window import MainWindow

STARS = [(60, 50), (150, 120), (100, 170)]


def _field(path):
    rng = np.random.default_rng(3)
    yy, xx = np.mgrid[:220, :220]
    img = rng.normal(100, 2, (220, 220))
    for (x, y), a in zip(STARS, (5000, 3000, 1500), strict=True):
        img += a * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 1.4**2))
    fits.PrimaryHDU(img.astype("float32")).writeto(path)
    return str(path)


def test_find_stars_fills_the_sources_tab_and_a_row_centres_the_star(qtbot, tmp_path):
    win = MainWindow(Settings(tmp_path / "cfg"))
    qtbot.addWidget(win)
    win.open_many([_field(tmp_path / "f.fits")])
    page = win.image_page
    iwin = win.area_windows["image"]
    assert "result_sources" not in iwin.docks  # made at its first content
    table = find_stars(iwin, page)
    assert len(table) == 3 and "result_sources" in iwin.docks
    assert np.allclose(sorted(zip(table["x"], table["y"], strict=True)), sorted(STARS), atol=1.0)
    page.viewer.zoom(8)  # zoomed in, so that there is room to centre
    view = page.sources_view
    row = int(np.argmin(np.abs(np.asarray(table["x"]) - 150)))
    view.row_chosen.emit(row)
    assert page.viewer.marker_list[0][:2] == (table["x"][row], table["y"][row])
    centre = page.viewer.mapToScene(page.viewer.viewport().rect().center())
    assert abs(centre.x() - (table["x"][row] + 0.5)) < 3
    win.engine.shutdown()

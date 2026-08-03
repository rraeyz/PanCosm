"""Undo / redo (Edit menu, Ctrl+Z / Ctrl+Y) on the pages where the user edits: what IRAF never had."""

import numpy as np
import pytest
from astropy.io import fits
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from astrowb.settings import Settings


@pytest.fixture
def window(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    win.show()
    yield win
    win.engine.shutdown()


def keys(win, *seq):
    for key, mod in seq:
        QTest.keyClick(win, key, mod)


UNDO, REDO = (Qt.Key_Z, Qt.ControlModifier), (Qt.Key_Y, Qt.ControlModifier)


def test_stars_marked_on_the_photometry_page(window, tmp_path):
    p = tmp_path / "f.fits"
    fits.PrimaryHDU(np.random.default_rng(1).normal(100, 3, (80, 100)).astype(np.float32)).writeto(p)
    window.show_workspace("photometry")
    page = window.photometry_page
    page.set_images([str(p)])
    page._clicked(30.0, 40.0)
    page._clicked(60.0, 20.0)
    assert page.target == (30.0, 40.0) and page.comps == [(60.0, 20.0)]
    assert window.undo_action.isEnabled() and "mark" in window.undo_action.text().lower()
    keys(window, UNDO)
    assert page.comps == [] and page.target == (30.0, 40.0)
    keys(window, UNDO)
    assert page.target is None
    keys(window, REDO, REDO)
    assert page.target == (30.0, 40.0) and page.comps == [(60.0, 20.0)]
    page.edit("clear", page._clear)
    keys(window, UNDO)
    assert page.comps == [(60.0, 20.0)]


def test_light_curve_edits_on_the_period_page(window):
    window.show_workspace("timeseries")
    pp = window.period_page
    t = np.linspace(0, 10, 300)
    y = 1 + 0.05 * np.sin(t) + np.random.default_rng(2).normal(0, 0.002, t.size)
    y[7] = 5.0
    pp.set_light_curve(t, y, "test")
    pp.edit("remove outliers", pp._clip)
    assert len(pp.time) == 299
    pp.edit("flux / magnitude", pp._convert)
    assert pp.magnitudes
    keys(window, UNDO)
    assert not pp.magnitudes and len(pp.time) == 299
    keys(window, UNDO)
    assert len(pp.time) == 300 and max(pp.flux) == 5.0
    keys(window, REDO)
    assert len(pp.time) == 299


def test_header_change_on_the_images_page(window, tmp_path):
    p = tmp_path / "h.fits"
    fits.PrimaryHDU(np.zeros((10, 10), np.float32), fits.Header({"OBJECT": "M 31"})).writeto(p)
    window.open_fits(p)
    page = window.image_page
    page.edit("change a keyword", page.set_keyword, "OBJECT", "M 33", "")
    assert page.header_set == {"OBJECT": ["M 33", ""]}
    keys(window, UNDO)
    assert page.header_set == {} and not page.header_save.isEnabled()
    keys(window, REDO)
    assert page.header_set["OBJECT"][0] == "M 33"


def test_identified_lines_on_the_echelle_tab(window):
    window.show_workspace("spectroscopy")
    sp = window.spectro_page
    sp.tabs.setCurrentWidget(sp.echelle_tab)
    ech = sp.echelle_tab
    ech.edit("identify a line", ech._add_line, ["58", "1063.52", ""])
    ech.guesses.item(0, 2).setText("5888.5841")  # typed by the user
    assert ech.undo_stack.count() == 2
    keys(window, UNDO)
    assert ech.guesses.item(0, 2).text() == ""
    keys(window, UNDO)
    assert ech.guesses.rowCount() == 0
    keys(window, REDO, REDO)
    assert ech.guesses.item(0, 2).text() == "5888.5841"

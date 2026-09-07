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


def area_in_front(window, key):
    """The area's own window (interface I4), in front with the keyboard, as after a user's click on it."""
    area = window.area_windows[key]
    area.raise_()
    area.activateWindow()
    QTest.qWaitForWindowActive(area)
    QTest.qWait(50)  # offscreen, the application takes the activation a moment later
    return area


def test_stars_marked_on_the_photometry_page(window, tmp_path):
    p = tmp_path / "f.fits"
    fits.PrimaryHDU(np.random.default_rng(1).normal(100, 3, (80, 100)).astype(np.float32)).writeto(p)
    window.show_workspace("photometry")
    page = window.photometry_page
    page.set_images([str(p)])
    page._clicked(30.0, 40.0)
    page._clicked(60.0, 20.0)
    assert page.target == (30.0, 40.0) and page.comps == [(60.0, 20.0)]
    area = area_in_front(window, "photometry")  # Photometry has its own window and Edit menu (interface I4)
    assert area.undo_action.isEnabled() and "mark" in area.undo_action.text().lower()
    keys(area, UNDO)
    assert page.comps == [] and page.target == (30.0, 40.0)
    keys(area, UNDO)
    assert page.target is None
    keys(area, REDO, REDO)
    assert page.target == (30.0, 40.0) and page.comps == [(60.0, 20.0)]
    page.edit("clear", page._clear)
    keys(area, UNDO)
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
    area = area_in_front(window, "timeseries")  # Undo follows the tab shown (Period search)
    keys(area, UNDO)
    assert not pp.magnitudes and len(pp.time) == 299
    keys(area, UNDO)
    assert len(pp.time) == 300 and max(pp.flux) == 5.0
    keys(area, REDO)
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
    area = area_in_front(window, "spectroscopy")  # Undo follows the tab shown (Echelle)
    keys(area, UNDO)
    assert ech.guesses.item(0, 2).text() == ""
    keys(area, UNDO)
    assert ech.guesses.rowCount() == 0
    keys(area, REDO, REDO)
    assert ech.guesses.item(0, 2).text() == "5888.5841"


def test_spectrum_tools_changes_go_through_ctrl_z(window, tmp_path):
    from astrowb.spectroscopy import spectrum_io

    w = np.linspace(6400, 6700, 600)
    path = spectrum_io.write(tmp_path / "s.fits", w, 200 + 0.1 * (w - 6400), np.zeros(w.size))
    window.show_workspace("spectroscopy")
    sp = window.spectro_page
    sp.tabs.setCurrentWidget(sp.tools_tab)
    tab = sp.tools_tab
    assert tab._open(str(path))
    raw = tab.flux.copy()
    tab._normalise()
    tab.step.setValue(2.0)
    tab._resample()
    assert tab.wave.size < w.size and abs(np.median(tab.flux) - 1) < 0.01
    area = area_in_front(window, "spectroscopy")
    keys(area, UNDO)
    assert tab.wave.size == w.size and abs(np.median(tab.flux) - 1) < 0.01
    keys(area, UNDO)
    assert np.array_equal(tab.flux, raw)
    keys(area, REDO, REDO)
    assert tab.wave.size < w.size
    tab._undo()  # the tab's own Undo button is the same step back
    assert tab.wave.size == w.size


def test_plan_targets(window):
    window.show_workspace("plan")
    page = window.plan_page
    page.add_target({"name": "AI Dra", "ra": 254.0758, "dec": 52.6983, "source": "test"})
    page.add_target({"name": "V505 Per", "ra": 32.4, "dec": 54.5, "source": "test", "t0": 2450000.0, "period": 4.2})
    page.table.item(0, 4).setText("1.1988")  # typed by the user
    page.table.cellWidget(1, 6).setChecked(True)
    area = area_in_front(window, "plan")  # in its own window (interface I4)
    keys(area, UNDO)
    assert not page.table.cellWidget(1, 6).isChecked()
    keys(area, UNDO)
    assert page.table.item(0, 4).text() == ""
    keys(area, UNDO)
    assert page.table.rowCount() == 1
    keys(area, REDO, REDO, REDO)
    assert page.table.rowCount() == 2 and page.table.cellWidget(1, 6).isChecked()
    page.table.setCurrentCell(0, 0)
    page.edit("remove a target", page.table.removeRow, 0)
    assert page.targets()[0]["name"] == "V505 Per"
    keys(area, UNDO)
    assert page.targets()[0]["name"] == "AI Dra" and page.table.item(0, 4).text() == "1.1988"


def test_observe_exposure_rows(window):
    window.show_workspace("observe")
    page = window.observe_page
    assert page.undo_stack.count() == 0  # the first row is the page's start, not a step
    page.edit("add an exposure row", page.add_exposure_row)
    page.exposures.cellWidget(1, 2).setValue(120)
    page.exposures.item(1, 1).setText("V")
    area = area_in_front(window, "observe")  # in its own window (interface I4)
    keys(area, UNDO)
    assert page.exposures.item(1, 1).text() == ""
    keys(area, UNDO)
    assert page.exposures.cellWidget(1, 2).value() == 60
    keys(area, UNDO)
    assert page.exposures.rowCount() == 1
    keys(area, REDO, REDO, REDO)
    spec = page.sequence_spec()["targets"][0]["exposures"]
    assert len(spec) == 2 and spec[1]["exptime"] == 120 and spec[1]["filter"] == "V"


def test_models_parameters(window):
    window.show_workspace("orbits")
    page = window.models_page
    page.table.item(0, 1).setText("2.5")  # period typed
    page.checks["incl"].setChecked(not page.checks["incl"].isChecked())
    before = page.undo_state()
    from astrowb.models.fit import NAMES

    page.edit("fitted values", page._fill_values, dict.fromkeys(NAMES, 0.25))
    assert page.table.item(0, 1).text() == "0.25"
    area = area_in_front(window, "orbits")  # Models has its own window (interface I4)
    keys(area, UNDO)
    assert page.undo_state() == before
    keys(area, UNDO, UNDO)
    assert page.table.item(0, 1).text() != "2.5"
    keys(area, REDO, REDO, REDO)
    assert page.table.item(0, 1).text() == "0.25"

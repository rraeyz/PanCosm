"""The branch after a user answers a dialog: a chosen file that is gone, empty or not what the page reads must be
said on the page, never raised (the earlier crash sweeps cancelled every dialog, so these branches never ran)."""

import pytest
from PySide6.QtWidgets import QFileDialog, QMessageBox

from astrowb.settings import Settings


@pytest.fixture
def window(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path / "cfg"))
    qtbot.addWidget(win)
    yield win
    win.engine.shutdown()


@pytest.fixture
def answer(monkeypatch):
    """Make the file dialogs answer with a path (the way a user picks one)."""

    def choose(path):
        monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(path), "")))
        monkeypatch.setattr(QFileDialog, "getOpenFileNames", staticmethod(lambda *a, **k: ([str(path)], "")))
        monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(path), "")))
        monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: QMessageBox.Ok))

    return choose


@pytest.fixture(params=["missing", "empty", "garbage"])
def chosen(request, tmp_path):
    if request.param == "missing":
        return tmp_path / "gone" / "x.csv"
    p = tmp_path / f"{request.param}.fits"  # named like an image: it is read, not skipped by its ending
    p.write_bytes(b"" if request.param == "empty" else b"\x00\xffnot a file\n1,2\nabc")
    return p


def test_oc_load_unreadable_file(window, answer, chosen):
    answer(chosen)
    window.oc_page._load()


def test_period_load_unreadable_file(window, answer, chosen):
    answer(chosen)
    window.lightcurve_page.period_page._load()


def test_visual_orbit_load_missing_file(qtbot, answer, tmp_path):
    from astrowb.ui.visual_orbit_tab import VisualOrbitTab

    tab = VisualOrbitTab()
    qtbot.addWidget(tab)
    answer(tmp_path / "gone.txt")
    tab._load()
    assert "Cannot read" in tab.status.text()


def test_observatory_dialog_open_unreadable_file(qtbot, answer, chosen, tmp_path):
    from astrowb.ui.observatory_dialog import ObservatoryDialog

    dlg = ObservatoryDialog(Settings(tmp_path / "cfg2"))
    qtbot.addWidget(dlg)
    answer(chosen)
    dlg._open_dialog()
    assert "Cannot read" in dlg.status.text()


def test_settings_profile_from_unreadable_image(window, answer, chosen):
    from astrowb.ui.settings_window import SettingsWindow

    dlg = SettingsWindow(window)
    answer(chosen)
    assert dlg.fill_from_header() == 0


def test_photometry_choose_unreadable_images(window, answer, chosen):
    page = window.photometry_page
    answer(chosen)
    page._choose_images()
    assert page.images == []


def test_publication_figure_of_an_empty_plot(window, answer, tmp_path):
    from astrowb.ui.plot.toolbar import PlotToolbar

    bar = PlotToolbar(window.oc_page.plot)
    assert bar.export_publication(str(tmp_path / "f.pdf")) is None

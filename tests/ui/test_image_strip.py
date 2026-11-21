"""UI-16.10: the file strip's thumbnails-or-list switch and "Follow a folder"."""

import numpy as np
from astropy.io import fits
from PySide6.QtWidgets import QListView

from astrowb.settings import Settings
from astrowb.ui.main_window import MainWindow


def _fits(path):
    fits.PrimaryHDU(np.random.default_rng(1).random((20, 20)).astype("float32")).writeto(path)
    return str(path)


def _page(qtbot, tmp_path):
    win = MainWindow(Settings(tmp_path / "cfg"))
    qtbot.addWidget(win)
    return win, win.image_page


def test_switch_keeps_the_selection(qtbot, tmp_path):
    win, page = _page(qtbot, tmp_path)
    page.add_open([_fits(tmp_path / f"f{i}.fits") for i in range(3)])
    page.open_list.setCurrentRow(1)
    page.thumbs_button.setChecked(True)
    assert page.open_list.viewMode() == QListView.IconMode and page.open_list.currentRow() == 1
    page.thumbs_button.setChecked(False)
    assert page.open_list.viewMode() == QListView.ListMode and page.open_list.currentRow() == 1
    win.engine.shutdown()


def test_followed_folder_adds_new_files(qtbot, tmp_path, monkeypatch):
    win, page = _page(qtbot, tmp_path)
    watched = tmp_path / "night"
    watched.mkdir()
    old = _fits(watched / "old.fits")
    page.follower.start(watched)
    new = _fits(watched / "new.fits")
    qtbot.waitUntil(lambda: new in page.open_paths(), timeout=5000)
    assert old not in page.open_paths()
    page.follower.stop()
    win.engine.shutdown()

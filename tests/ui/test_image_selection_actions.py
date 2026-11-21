"""UI-16.10: per-file actions on the files selected in the strip, and the layer opacity slider."""

import numpy as np
from astropy.io import fits

from astrowb.settings import Settings
from astrowb.ui.image_selection import blink_selected, close_selected, save_selected
from astrowb.ui.main_window import MainWindow


def _fits(path):
    fits.PrimaryHDU(np.random.default_rng(1).random((20, 20)).astype("float32")).writeto(path)
    return str(path)


def _setup(qtbot, tmp_path, n=4):
    win = MainWindow(Settings(tmp_path / "cfg"))
    qtbot.addWidget(win)
    paths = [_fits(tmp_path / f"f{i}.fits") for i in range(n)]
    win.open_many(paths)
    return win, win.image_page, paths


def _select(page, rows):
    page.open_list.clearSelection()
    for r in rows:
        page.open_list.item(r).setSelected(True)


def test_close_selected_closes_each_and_shows_the_neighbour(qtbot, tmp_path):
    win, page, paths = _setup(qtbot, tmp_path)
    _select(page, [0, 1])  # f0 is the shown one
    close_selected(page, win)
    assert page.open_paths() == paths[2:] and str(win.current_path) == paths[2]
    win.engine.shutdown()


def test_save_selected_copies_each_file(qtbot, tmp_path):
    win, page, paths = _setup(qtbot, tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    _select(page, [1, 3])
    tasks = save_selected(page, win, folder=str(out))
    assert len(tasks) == 2
    qtbot.waitUntil(lambda: sorted(p.name for p in out.iterdir()) == ["f1.fits", "f3.fits"], timeout=10000)
    win.engine.shutdown()


def test_blink_selected_takes_only_the_selection(qtbot, tmp_path):
    win, page, paths = _setup(qtbot, tmp_path)
    _select(page, [2])
    assert blink_selected(page, win) is None  # one file is no series
    _select(page, [1, 2])
    dlg = blink_selected(page, win)
    qtbot.addWidget(dlg)
    assert len(dlg.paths) == 2
    win.engine.shutdown()


def test_layer_opacity_slider_fades_the_chosen_layer(qtbot, tmp_path):
    from PySide6.QtWidgets import QGraphicsRectItem

    win, page, _ = _setup(qtbot, tmp_path, 1)
    viewer = page.viewer
    item = QGraphicsRectItem(0, 0, 5, 5)
    viewer.scene().addItem(item)
    viewer._overlays["Test"] = [item]
    lst = page.layers_panel.list
    lst.refresh()
    lst.setCurrentRow(0)
    assert lst.opacity.isEnabled()
    lst.opacity.setValue(40)
    assert abs(item.opacity() - 0.4) < 1e-6 and viewer.layer_opacity("Test") == item.opacity()
    win.engine.shutdown()

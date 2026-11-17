"""A save into a folder that is gone (or read-only, or full) shows a message; it never raises (owner's rule)."""

import types

import numpy as np
import pytest
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from astrowb.ui import messages


@pytest.fixture
def boxes(monkeypatch, tmp_path):
    """The dialog answers a path in a missing folder; the warnings are collected."""
    gone = str(tmp_path / "gone" / "x.csv")
    seen = []
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (gone, ""))
    monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text, *a: seen.append(text))
    return types.SimpleNamespace(path=gone, seen=seen)


def test_guarded_shows_the_error_and_returns_none(boxes, qtbot):
    w = QWidget()
    qtbot.addWidget(w)
    assert messages.guarded(w, open, boxes.path, "w") is None
    assert len(boxes.seen) == 1 and "gone" in boxes.seen[0]
    assert messages.guarded(w, lambda: 7) == 7 and len(boxes.seen) == 1


def test_the_plot_canvas_exports_say_so(boxes, qtbot):
    from astrowb.ui.kit.widgets import PlotCanvas

    p = PlotCanvas()
    qtbot.addWidget(p)
    p.figure.subplots().plot([1, 2], [3, 4])
    assert p.export_data() is None
    assert p.export_publication() is None
    assert len(boxes.seen) == 2


def test_the_table_menu_export_says_so(boxes, qtbot):
    from astrowb.ui.kit.table_view import DataTable

    t = DataTable()
    qtbot.addWidget(t)
    t.set_data(["A", "B"], [["a", 1.0], ["b", 2.0]], keys=["a", "b"])
    t._menu(t.table.rect().center()).actions()[2].trigger()
    assert len(boxes.seen) == 1


def test_the_chooser_export_says_so(boxes, qtbot, tmp_path):
    from astrowb.settings import Settings
    from astrowb.ui.profile_chooser import ProfileChooser

    host = QWidget()
    qtbot.addWidget(host)
    host.settings, host.profile_controls, host._show_scale = Settings(tmp_path), {}, lambda: None
    assert ProfileChooser(host).export() is None
    assert len(boxes.seen) == 1


def test_the_measurements_and_graph_exports_say_so(boxes, qtbot):
    from astrowb.ui.image_page import ImagePage
    from astrowb.ui.photometry_page import PhotometryPage

    w = QWidget()
    qtbot.addWidget(w)
    w._meas_cols, w._meas_rows, w._meas_shown = {"a": [1.0, 2.0]}, [0, 1], ["a"]
    assert PhotometryPage.export_measurements(w) is None
    w._graph_data = (["x", "y"], np.arange(3.0), np.arange(3.0))
    assert ImagePage.export_graph(w) is None
    assert len(boxes.seen) == 2


def test_the_regions_export_says_so(boxes, qtbot):
    from astrowb.ui import overlay_actions as oa

    win = QWidget()
    qtbot.addWidget(win)
    win.viewer = types.SimpleNamespace(marker_list=[(1.0, 2.0, 3.0, "red", "T")])
    win.wcs = None
    assert oa.save_regions(win) is None
    assert len(boxes.seen) == 1

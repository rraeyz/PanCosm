"""UI-10 / UI-11: every plot and table in every area window carries the standard's pieces."""

import importlib.util
import sys
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

TOOL = Path(__file__).resolve().parents[1] / "tools" / "ui_gallery.py"
# UI-11 still left: these windows hold plain QTableWidgets (their own export / copy menu, no count line, no header
# menu); each is bound to its window's code (edits, clicks, per-cell marks) and moves to TableView one by one.
PLAIN_TABLES = {"plan", "photometry", "automation"}  # fmt: skip


def _gallery():
    spec = importlib.util.spec_from_file_location("ui_gallery", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.slow
@pytest.mark.skipif(sys.platform != "linux", reason="windows built as the gallery builds them")
def test_every_plot_has_a_toolbar_and_every_table_a_house_widget(qapp, tmp_path):
    from PySide6.QtWidgets import QTableWidget

    from astrowb.settings import Settings
    from astrowb.ui.kit.table import TableView
    from astrowb.ui.kit.table_view import DataTable
    from astrowb.ui.kit.widgets import PlotCanvas
    from astrowb.ui.main_window import MainWindow
    from astrowb.ui.plot.toolbar import PlotToolbar
    from astrowb.ui.plot.view import PlotView

    main = MainWindow(Settings(tmp_path / "s"))
    bare, tables = [], []
    try:
        for key, win in _gallery().windows(main):
            win.show()
            qapp.processEvents()
            toolbars = {tb.view for tb in win.findChildren(PlotToolbar)}
            bare += [f"{key}: {v.objectName() or type(v.parent()).__name__}" for v in win.findChildren(PlotView)
                     if v not in toolbars and not v.property("embedded")]  # fmt: skip
            for c in win.findChildren(PlotCanvas):
                # the matplotlib exceptions (sky chart, corner plot, 3-D surface) keep what PlotCanvas offers
                assert "Axis limits…" in [a.text() for a in c.context_menu().actions()], key
            if any(not isinstance(t.parent(), (DataTable, TableView)) for t in win.findChildren(QTableWidget)):
                tables.append(key)
            win.close()
    finally:
        main.engine.shutdown()
        main.close()
    assert not bare, bare
    assert set(tables) <= PLAIN_TABLES, set(tables) - PLAIN_TABLES

"""PLN-W: the finder adds every selected row as a target in one undo step, and skips those already there."""

from pathlib import Path

from PySide6.QtCore import QDate, QItemSelectionModel
from PySide6.QtWidgets import QAbstractItemView

from astrowb.settings import Settings

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "exoplanet_archive_sample.csv"


def _finder(qtbot, tmp_path):
    from astrowb.ui.plan_finder import FinderDialog
    from astrowb.ui.plan_page import PlanPage

    page = PlanPage(Settings(tmp_path))
    qtbot.addWidget(page)
    page.lat.setValue(39.84)
    page.lon.setValue(32.78)
    page.min_alt.setValue(30)
    page.date.setDate(QDate(2026, 11, 14))
    dlg = FinderDialog(page, lambda url: SAMPLE.read_text(encoding="utf-8"))
    qtbot.addWidget(dlg)
    dlg.load()
    qtbot.waitUntil(lambda: len(dlg.events) >= 3, timeout=20000)
    return page, dlg


def _select(dlg, rows):
    t = dlg.view.table
    t.clearSelection()
    for r in rows:  # as Ctrl-clicks add rows
        t.selectionModel().select(t.model().index(r, 0), QItemSelectionModel.Select | QItemSelectionModel.Rows)


def test_three_selected_rows_become_three_targets(qtbot, tmp_path):
    page, dlg = _finder(qtbot, tmp_path)
    assert dlg.view.table.selectionMode() == QAbstractItemView.ExtendedSelection
    _select(dlg, [0, 1, 2])
    assert dlg.add_button.text() == "Add as targets"
    dlg.add_button.click()
    names = [page._cell(r, 0) for r in range(3)]
    assert names == [dlg.view.table.item(r, 0).text() for r in range(3)]
    page.undo_stack.undo()  # one step for all three
    assert page.table.rowCount() == 0


def test_a_target_already_there_is_skipped_and_said(qtbot, tmp_path):
    page, dlg = _finder(qtbot, tmp_path)
    _select(dlg, [1])
    assert dlg.add_button.text() == "Add as target"
    dlg.add_button.click()
    _select(dlg, [0, 1, 2])
    dlg.add_button.click()
    assert page.table.rowCount() == 3
    assert "1 already in the targets" in dlg.note.text()

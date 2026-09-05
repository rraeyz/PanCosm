"""The shared table and the plot's data export (plans/interface.md I2.6)."""

from PySide6.QtCore import Qt

from astrowb.ui.table_view import DataTable


def test_sort_filter_columns_marks_and_the_row_signal(qtbot):
    t = DataTable()
    qtbot.addWidget(t)
    t.set_data(["Frame", "FWHM", "Sky"], [["a.fits", 9.5, 100], ["b.fits", 10.2, 90], ["c.fits", 2.1, None]],
               keys=["/n/a.fits", "/n/b.fits", "/n/c.fits"])  # fmt: skip
    t.table.sortItems(1, Qt.AscendingOrder)
    assert [t.table.item(r, 1).text() for r in range(3)] == ["2.1", "9.5", "10.2"]  # numbers, not text
    with qtbot.waitSignal(t.row_chosen) as sig:
        t.table.setCurrentCell(2, 0)
    assert sig.args == ["/n/b.fits"]  # the key follows its row after sorting
    t.filter.setText("b.fits")
    assert [t.table.isRowHidden(r) for r in range(3)] == [True, True, False]
    t.filter.setText("")
    menu = t._column_menu(t.table.horizontalHeader().rect().center())
    menu.actions()[2].setChecked(False)
    assert t.table.isColumnHidden(2)
    t.mark(0, 1, "#e5484d", "too wide: clouds?")
    assert t.table.item(0, 1).toolTip() == "too wide: clouds?"
    assert [a.text() for a in t._menu(t.table.rect().center()).actions()] == [
        "Copy", "Copy table", "Export table (CSV or LaTeX)…"
    ]  # fmt: skip


def test_plot_exports_its_numbers(qtbot, tmp_path):
    import csv

    from astrowb.ui.widgets import PlotCanvas

    p = PlotCanvas()
    qtbot.addWidget(p)
    ax = p.figure.subplots()
    ax.plot([1, 2, 3], [4, 5, 6], label="target")
    ax.scatter([1.5], [7])
    ax.set_ylabel("Relative flux")
    rows = list(csv.reader(open(p.export_data(tmp_path / "plot.csv"), encoding="utf-8")))
    assert rows[0] == ["axis", "series", "x", "y"]
    assert rows[1] == ["Relative flux", "target", "1.0", "4.0"] and rows[-1][1:] == ["series 2", "1.5", "7.0"]

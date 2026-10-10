"""ARC-8: filter expressions, writers that read back, and the virtual table view with a million rows."""

import time

import numpy as np
import pytest
from astropy import units as u
from astropy.table import Table

from astrowb.core import table as T


def minima():
    t = Table()
    t["cycle"] = [0, 1, 2, 3]
    t["bjd"] = [2460512.123456, 2460512.523451, np.nan, 2460513.323449] * u.day
    t["bjd_err"] = [0.000123, 0.00009, 0.0001, 0.00031]
    t["type"] = ["I", "II", "I", "II"]
    t["bjd"].description = "time of minimum"
    return t


def test_select_expressions_and_their_errors():
    t = minima()
    assert T.select(t, "").all()
    assert list(T.select(t, "bjd_err < 0.0002 and not isnan(bjd)")) == [True, True, False, False]
    assert list(T.select(t, "1 <= cycle < 3 or abs(bjd_err - 0.00031) < 1e-9")) == [False, True, True, True]
    assert list(T.select(t, "cycle * 2 > 3")) == [False, False, True, True]
    for bad, why in (("nope > 1", "no column nope"), ("__import__('os')", "not understood"),
                     ("bjd.real > 0", "not understood"), ("cycle >", "not understood")):  # fmt: skip
        with pytest.raises(ValueError, match=why):
            T.select(t, bad)


def test_writers_read_back_and_latex_rounds_by_the_error(tmp_path):
    t = minima()
    for ext, fmt in ((".csv", "ascii.csv"), (".ecsv", "ascii.ecsv"), (".vot", "votable"), (".html", "ascii.html")):
        back = Table.read(T.write(t, tmp_path / f"m{ext}"), format=fmt)
        assert list(back["cycle"]) == [0, 1, 2, 3] and back["bjd"][0] == pytest.approx(2460512.123456)
    assert Table.read(tmp_path / "m.ecsv")["bjd"].unit == u.day
    tex = T.write(t, tmp_path / "m.tex", caption="Times of minimum").read_text(encoding="utf-8")
    assert r"\colhead{bjd [d]}" in tex and r"2460512.12346 $\pm$ 0.00012 & I \\" in tex
    assert r"\tablecaption{Times of minimum}" in tex and "bjd_err" not in tex
    md = T.write(t, tmp_path / "m.md").read_text(encoding="utf-8").splitlines()
    assert md[0] == "| cycle | bjd [d] | type |" and md[2].startswith("| 0 | 2460512.12346 ± 0.00012 | I |")
    with pytest.raises(ValueError):
        T.write(t, tmp_path / "m.fits")


@pytest.fixture
def big():
    rng = np.random.default_rng(3)
    t = Table({f"c{i}": rng.normal(size=1_000_000) for i in range(40)})
    t["c0"][5] = np.nan
    return t


def test_a_million_rows_open_sort_and_filter_quickly(qapp, big):
    from astrowb.ui.kit.table import TableView

    v = TableView()
    v.resize(900, 500)
    v.show()
    start = time.perf_counter()
    v.set_table(big)
    qapp.processEvents()
    assert time.perf_counter() - start < 0.5
    start = time.perf_counter()
    v._sort_by(0)
    qapp.processEvents()
    assert time.perf_counter() - start < 1.0
    rows = v.shown_rows()
    assert big["c0"][rows[0]] == np.nanmin(big["c0"]) and rows[-1] == 5  # NaN last
    v._sort_by(0)  # second click: descending, NaN still last
    assert big["c0"][v.shown_rows()[0]] == np.nanmax(big["c0"]) and v.shown_rows()[-1] == 5
    v.filter.setText("c1 > 3")
    v._apply()
    assert len(v.shown_rows()) == int((big["c1"] > 3).sum())
    v.close()


def test_rows_chosen_marks_copy_and_export_follow_sort_and_filter(qapp, tmp_path):
    from PySide6.QtCore import Qt

    from astrowb.ui.kit.table import TableView

    v = TableView()
    v.set_table(minima(), marks={(3, "bjd"): ("#ffcdd2", "poor coverage")})
    chosen = []
    v.row_chosen.connect(chosen.append)
    v._sort_by(v.model.table.colnames.index("bjd_err"))  # ascending: rows 1, 2, 0, 3
    assert list(v.shown_rows()) == [1, 2, 0, 3]
    v.view.selectRow(3)
    assert chosen[-1] == 3 and v.selected_rows() == [3]
    index = v.model.index(3, 1)
    assert v.model.data(index, Qt.ToolTipRole) == "poor coverage"
    assert v.model.data(v.model.index(1, 1)) == ""  # NaN shown empty
    assert v.copy_text().splitlines()[1].startswith("3\t2460513.323449\t")
    v.filter.setText("type == 0")  # a text column cannot be compared with a number: shown, not raised
    v._apply()
    v.view.setColumnHidden(3, True)
    v.filter.setText("cycle >= 2")
    v._apply()
    back = Table.read(v.export(tmp_path / "shown.ecsv"))
    assert list(back["cycle"]) == [2, 3] and "type" not in back.colnames
    v.close()


def test_table_and_plot_select_together(qapp):
    from PySide6.QtWidgets import QAbstractItemView

    from astrowb.ui.kit.link import link
    from astrowb.ui.kit.table import TableView
    from astrowb.ui.plot.spec import AxisSpec, FigureSpec, PanelSpec, SeriesSpec
    from astrowb.ui.plot.view import PlotView

    t = minima()
    plot = PlotView(FigureSpec([PanelSpec(AxisSpec("cycle"), AxisSpec("err"), [
        SeriesSpec("minima", t["cycle"], t["bjd_err"], pickable=True, ids=list(range(len(t))))])]))  # fmt: skip
    table = TableView()
    table.set_table(t)
    table.view.setSelectionMode(QAbstractItemView.ExtendedSelection)
    select_rows = link(table, plot, "minima")
    table._sort_by(0)
    table._sort_by(0)  # descending: shown order 3, 2, 1, 0
    table.view.selectRow(0)
    ring = plot.items[0]["ring"]
    assert list(ring.getData()[0]) == [3]
    plot.point_clicked.emit("minima", 1)
    assert table.selected_rows() == [1] and list(ring.getData()[0]) == [1]
    plot.points_selected.emit("minima", [0, 2])
    assert table.selected_rows() == [0, 2]
    select_rows([])
    assert table.selected_rows() == [] and len(ring.getData()[0]) == 0


def test_editable_columns_check_the_kind_and_report_each_change(qapp):
    from PySide6.QtCore import Qt

    from astrowb.ui.kit.table import TableView

    v = TableView()
    t = minima()
    v.set_table(t, editable=("bjd_err", "type"))
    edits = []
    v.model.edited.connect(lambda *e: edits.append(e))
    err_col, type_col, cycle_col = (t.colnames.index(c) for c in ("bjd_err", "type", "cycle"))
    assert not v.model.flags(v.model.index(0, cycle_col)) & Qt.ItemIsEditable
    assert v.model.flags(v.model.index(0, err_col)) & Qt.ItemIsEditable
    assert not v.model.setData(v.model.index(0, err_col), "abc")  # not a number: refused
    assert v.model.setData(v.model.index(0, err_col), "0,0002")  # a decimal comma is read
    assert t["bjd_err"][0] == 0.0002 and edits == [(0, "bjd_err", 0.000123, 0.0002)]
    assert v.model.setData(v.model.index(1, type_col), "I")
    v.model.set_value(0, "bjd_err", 0.000123)  # undo, as a window's undo step does it
    assert t["bjd_err"][0] == 0.000123 and len(edits) == 2

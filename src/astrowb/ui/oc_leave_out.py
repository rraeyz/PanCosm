"""Leaving O−C points out and bringing them back from the diagram (UI-16.5, OC-W). The points the user selected (a
click, or a lasso: L + drag) are rows of the minima table, found by the minimum's time; Delete or "Leave out the
selected" unticks their Use cells, "Bring back the selected" reticks them, each as one undoable step, and a fit already
made is repeated. Left-out minima stay on the diagram as grey points."""

import numpy as np
from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtCore import QItemSelectionModel as Sel
from PySide6.QtWidgets import QPushButton

from ..timeseries.ephemeris import Minimum, epochs
from .kit import tokens
from .oc_minima_table import KIND, USE
from .oc_point_select import _row_of, _time
from .plot.spec import SeriesSpec

translate = QCoreApplication.translate
NAME = "left out"  # the series' name in code; shown translated


def use_state(page):
    t = page.minima_input
    return {t.item(r, 1).text(): t.item(r, USE).checkState() == Qt.Checked for r in range(t.rowCount())}


def restore(page, state):
    t = page.minima_input
    for r in range(t.rowCount()):
        use = state.get(t.item(r, 1).text())
        if use is not None:
            t.item(r, USE).setCheckState(Qt.Checked if use else Qt.Unchecked)
    _refit(page)


def _refit(page):
    if page.fit_result is not None:
        page.run_fit()


def set_use(page, use):
    """Tick or untick the selected rows as one undo step."""
    t = page.minima_input
    rows = {i.row() for i in t.selectedItems()}

    def apply():
        for r in rows:
            t.item(r, USE).setCheckState(Qt.Checked if use else Qt.Unchecked)

    before = use_state(page)
    page.edit(
        translate("OcLeaveOut", "Bring back minima") if use else translate("OcLeaveOut", "Leave out minima"), apply
    )
    if use_state(page) != before:
        _refit(page)


def left_out_series(page, f):
    """Grey, pickable points of the unticked minima on the fit's reference ephemeris."""
    t, minima = page.minima_input, []
    for r in range(t.rowCount()):
        if t.item(r, USE).checkState() != Qt.Checked and _time(t, r) is not None:
            minima.append(Minimum(_time(t, r), None, t.item(r, KIND).text(), "", None))
    if not minima:
        return []
    times = np.array([m.time for m in minima])
    e = epochs(minima, f.ref_t0, f.ref_period)
    return [SeriesSpec(translate("OcLeaveOut", NAME), e, (times - (f.ref_t0 + f.ref_period * e)) * 1440,
                       colour=tokens.role("rejected"), pickable=True, ids=times)]  # fmt: skip


def connect(page):
    table = page.minima_input

    def lassoed(_name, ids):  # one signal per series: the lasso adds to what is selected
        for time in ids:
            r = _row_of(table, time)
            if r is not None:
                table.selectionModel().select(table.model().index(r, 1), Sel.Select | Sel.Rows)

    page.plot.points_selected.connect(lassoed)
    page.plot.key_pressed.connect(lambda key, _x: key == "delete" and set_use(page, False))
    box = page.stage_boxes["report"].layout()
    for text, use, tip in (
        (translate("OcLeaveOut", "Leave out the selected"), False,
         translate("OcLeaveOut", "Untick the selected minima (click or L + drag on the diagram; Delete too)")),
        (translate("OcLeaveOut", "Bring back the selected"), True,
         translate("OcLeaveOut", "Tick the selected left-out minima again (grey points on the diagram)")),
    ):  # fmt: skip
        b = QPushButton(text, page)
        b.setToolTip(tip)
        b.clicked.connect(lambda _=False, u=use: set_use(page, u))
        box.addWidget(b)
        setattr(page, "bring_back_button" if use else "leave_out_button", b)

"""The Light curves window's Fold and Report stages and the peak table in its inspector (plans/interface.md UI-16.4).
The page keeps the logic (`fold_at`, `step_peak`, `save_button`); the stages only host its controls."""

import numpy as np
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication, QFormLayout, QPushButton, QVBoxLayout, QWidget

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PeriodWindow", "…") calls

PEAKS = 10  # rows of the peak table: the highest local maxima of the periodogram


def peak_table(periodogram, n=PEAKS):
    """The n highest local maxima of the periodogram as a table (period, power), highest first; the search result
    holds no false-alarm probability or S/N, so there are no such columns."""
    from astropy.table import Table

    p, power = np.asarray(periodogram["periods"], float), np.asarray(periodogram["power"], float)
    order = np.argsort(p)
    p, power = p[order], power[order]
    k = np.flatnonzero((power[1:-1] > power[:-2]) & (power[1:-1] >= power[2:])) + 1
    k = k[np.argsort(power[k])[::-1][:n]]
    table = Table({"period": p[k], "power": power[k]})
    table["period"].unit = "d"
    return table


def fold_stage(page):
    """Phase bins (moved from the Search stage) and the neighbouring-peak steps (the ← → keys)."""
    column = page.guide.parentWidget().layout()  # the controls column, before its boxes are cut
    grid = next(
        sub
        for sub in map(column.itemAt, range(column.count()))
        if sub.layout() and sub.layout().indexOf(page.phase_bins) >= 0
    ).layout()
    label = grid.itemAtPosition(3, 0).widget()
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    form = QFormLayout()
    form.addRow(label, page.phase_bins)
    lay.addLayout(form)
    longer, shorter = (
        translate("PeriodWindow", "Folds at the next peak towards longer periods (→)"),
        translate("PeriodWindow", "Folds at the next peak towards shorter periods (←)"),
    )
    for text, tip, step in (
        (translate("PeriodWindow", "Next peak"), longer, 1),
        (translate("PeriodWindow", "Previous peak"), shorter, -1),
    ):
        button = QPushButton(text, box)
        button.setToolTip(tip)
        button.clicked.connect(lambda _=False, s=step: getattr(page, "periodogram", None) and page.step_peak(s))
        lay.addWidget(button)
    lay.addStretch(1)
    return box


def report_stage(page, table_view):
    """Save the light curve (moved from the Data stage) and copy the peak table."""
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.addWidget(page.save_button)
    copy = QPushButton(translate("PeriodWindow", "Copy the peak table"), box)
    copy.setToolTip(translate("PeriodWindow", "The peaks of the periodogram, as shown, as tab-separated text"))
    copy.clicked.connect(
        lambda: table_view.model.table is not None and QApplication.clipboard().setText(table_view.copy_text())
    )
    lay.addWidget(copy)
    lay.addStretch(1)
    return box


def peak_inspector(win, page):
    """The inspector: the peaks of the last search; a click on a row folds at that peak. Hidden until a search."""
    from .kit.table import TableView

    view = TableView(win)
    view.filter.hide()  # ten rows need no filter
    dock = win.set_inspector(view)
    dock.setWindowTitle(translate("PeriodWindow", "Peaks"))
    dock.hide()
    view.row_chosen.connect(lambda i: page.fold_at(float(view.model.table["period"][i])))
    show = page.show_result

    def show_result(out):
        show(out)
        view.set_table(peak_table(out))
        dock.show()

    page.show_result = show_result
    return view

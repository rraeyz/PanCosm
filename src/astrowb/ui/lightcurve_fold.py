"""The Light curves window's Fold and Report stages and the peak table in its inspector (plans/interface.md UI-16.4).
The page keeps the logic (`fold_at`, `step_peak`, `save_button`); the stages only host its controls."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication, QFormLayout, QPushButton, QVBoxLayout, QWidget

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PeriodWindow", "…") calls

PEAKS = 10  # rows of the peak table: the highest local maxima of the periodogram


def fap_text(fap):
    """A false-alarm probability for the table: scientific below 0.001, "—" when there is none."""
    return "—" if fap is None else f"{fap:.2e}" if fap < 0.001 else f"{fap:.3f}"


def peak_table(periodogram, n=PEAKS):
    """The n highest local maxima of the periodogram as a table (period, power, FAP), highest first. The FAP comes
    from the search step and exists for Lomb–Scargle periodograms only; other methods show "—"."""
    from astropy.table import Table

    from ..timeseries.significance import period_maxima

    p, power = period_maxima(periodogram["periods"], periodogram["power"], n)
    faps = periodogram.get("peak_faps")
    faps = faps if faps is not None and len(faps) == len(p) else [None] * len(p)
    snr = periodogram.get("peak_snr")
    snr = snr if snr is not None and len(snr) == len(p) else [None] * len(p)
    table = Table({"period": p, "power": power, "fap": [fap_text(f) for f in faps],
                   "snr": ["—" if v is None else f"{v:.1f}" for v in snr]})  # fmt: skip
    table.meta["snr"] = snr  # the raw values, for the marks of peak_marks
    table["period"].unit = "d"
    table["fap"].description = (
        translate("PeriodWindow", "False-alarm probability of the peak (Baluev 2008), Lomb–Scargle periodograms only")
        if any(f is not None for f in faps)
        else translate(
            "PeriodWindow", "A false-alarm probability exists only for Lomb–Scargle periodograms; not for this method"
        )
    )
    table["snr"].description = (
        translate(
            "PeriodWindow", "Amplitude over the mean residual amplitude spectrum within ±1 c/d (Breger et al. 1993)"
        )
        if any(v is not None for v in snr)
        else translate("PeriodWindow", "S/N is computed for Lomb–Scargle periodograms only; not for this method")
    )
    return table


def peak_marks(table):
    """{(row, "snr"): (colour, reason)} for the peaks below S/N 4, as the Frequencies table marks them."""
    from .kit import tokens

    reason = translate("PeriodWindow", "S/N below 4: not significant (Breger et al. 1993)")
    return {
        (i, "snr"): (tokens.role("saturated"), reason)
        for i, v in enumerate(table.meta["snr"])
        if v is not None and v < 4
    }


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
        table = peak_table(out)
        view.set_table(table, marks=peak_marks(table))
        dock.show()

    page.show_result = show_result
    return view

"""The editable minima table of the O−C window (plans/interface.md UI-16.5): the pasted or loaded text is read by
parse_minima into rows (Use, Time, Error, Type, Source, Weight); the fit reads the table, so a row can be left out or
down-weighted without editing the text. The Method column (CCD, pe, pg, vis or empty) comes from the text when a row
names it and can be edited; "Weight by method" turns it into the weights of timeseries.ephemeris_models."""

import re
from math import sqrt

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QCheckBox, QLabel, QPushButton, QTableWidgetItem

from ..timeseries.ephemeris import METHOD_CODES, Minimum, hjd_scale_unknown, parse_minima
from ..timeseries.ephemeris_models import weights_by_method
from .kit.table_view import DataTable

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("OcMinimaTable", "…") calls
USE, TIME, ERROR, KIND, SOURCE, WEIGHT, METHOD = range(7)  # Method last: the other columns keep their places
_WEIGHT_KEY = {"vis": "visual", "pg": "photographic", "pe": "electronic", "CCD": "electronic"}


def add_minima_table(page, layout):
    """The table under the paste box and a Paste button; the box stays the way text comes in."""
    frame = DataTable(page)
    frame.prepare(
        [translate("OcMinimaTable", h) for h in ("Use", "Time", "Error (d)", "Type", "Source", "Weight", "Method")]
    )
    frame.table.setObjectName("minima_input_table")
    frame.table.horizontalHeaderItem(METHOD).setToolTip(
        translate("OcMinimaTable", "CCD, pe (photoelectric), pg (photographic), vis (visual) or empty (not stated)")
    )
    page.minima_input = frame.table
    layout.addWidget(frame, 1)
    page.weight_by_method = QCheckBox(
        translate("OcMinimaTable", "Weight by method (visual 1, photographic 3, electronic 10)")
    )
    page.weight_by_method.setToolTip(
        translate(
            "OcMinimaTable",
            "Multiply each row's weight by its method's weight (vis 1, pg 3, pe and CCD 10). A row with no method "
            "keeps the weight its error gives, as without this option.",
        )
    )
    layout.addWidget(page.weight_by_method)
    page.minima_count, page.minima_standard = QLabel(page), QLabel(page)
    page.minima_count.setObjectName("minima_count")
    page.minima_standard.setObjectName("minima_standard")
    layout.addWidget(page.minima_count)
    layout.addWidget(page.minima_standard)
    paste = QPushButton(translate("OcMinimaTable", "Paste"), page)
    paste.setToolTip(translate("OcMinimaTable", "Replace the minima with the clipboard text, in any layout of the box"))
    paste.clicked.connect(lambda: page.text.setPlainText(QGuiApplication.clipboard().text()))
    page.paste_button = paste
    page.text.textChanged.connect(lambda: fill(page))
    page.text.textChanged.connect(lambda: show_summary(page))
    show_summary(page)
    return paste


def show_summary(page):
    """The count line and the time-standard line (ARC-15 item 4). A standard the text names is stated; HJD without a
    scale is taken as UTC (`hjd_scale_unknown`); anything else is not stated. The last two carry the warning mark."""
    text = page.text.toPlainText()
    try:
        minima = parse_minima(text)
    except ValueError:
        return
    n2 = sum(m.kind == "II" for m in minima)
    page.minima_count.setText(
        translate("OcMinimaTable", "{n} minima · {a} primary · {b} secondary").format(
            n=len(minima), a=len(minima) - n2, b=n2
        )
    )
    named = re.search(r"\b(HJD|BJD|JD|MJD)[ _]?(UTC|TT|TDB|TDT|UT)\b|\b(UTC|UT|TT|TDB|TDT)\b", text.upper())
    if named:
        line, tip = translate("OcMinimaTable", "time standard: {s}").format(s=named.group(0).replace(" ", "_")), ""
    elif hjd_scale_unknown(text, [m.time for m in minima]):
        line = translate("OcMinimaTable", "time standard: HJD (UTC assumed) ⚠")
        tip = translate(
            "OcMinimaTable",
            "The file says HJD without a time scale: taken as UTC. If the times are TT every O−C is later by "
            "TT − UTC; write UTC or TT in the text to state it.",
        )
    else:
        line = translate("OcMinimaTable", "time standard: not stated ⚠") if minima else ""
        tip = translate(
            "OcMinimaTable",
            "The text names no time standard. Write it in the text (for example HJD_UTC, BJD_TDB) to state it.",
        )
    page.minima_standard.setText(line)
    page.minima_standard.setToolTip(tip)


def _cell(text, flags=None):
    item = QTableWidgetItem(text)
    if flags is not None:
        item.setFlags(flags)
    return item


def fill(page):
    """Rebuild the rows from the text; Use and Weight of a time that was already there are kept. A text that does not
    parse leaves the table as it was and says why."""
    try:
        minima = parse_minima(page.text.toPlainText())
    except ValueError as e:
        page.result.setText(translate("OcMinimaTable", "Cannot read the minima: {error}").format(error=e))
        return
    t = page.minima_input
    kept = {
        t.item(r, TIME).text(): (t.item(r, USE).checkState(), t.item(r, WEIGHT).text(), t.item(r, METHOD).text())
        for r in range(t.rowCount())
    }
    t.blockSignals(True)
    t.setRowCount(len(minima))
    for r, m in enumerate(minima):
        use, weight, method = kept.get(repr(m.time), (Qt.Checked, "1", ""))
        check = _cell("", Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        check.setCheckState(use)
        fixed = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        t.setItem(r, USE, check)
        t.setItem(r, TIME, _cell(repr(m.time), fixed))
        t.setItem(r, ERROR, _cell("" if m.error is None else repr(m.error)))
        t.setItem(r, KIND, _cell(m.kind, fixed))
        t.setItem(r, SOURCE, _cell(m.source, fixed))
        t.setItem(r, WEIGHT, _cell(weight))
        t.setItem(r, METHOD, _cell(method or m.method or ""))
    t.blockSignals(False)


def minima_for_fit(page):
    """The ticked rows as Minimum. The fit takes errors, not weights: a weight w becomes sigma / sqrt(w)."""
    t, out = page.minima_input, []
    for r in range(t.rowCount()):
        if t.item(r, USE).checkState() != Qt.Checked:
            continue
        try:
            error = float(t.item(r, ERROR).text()) if t.item(r, ERROR).text().strip() else None
            w = float(t.item(r, WEIGHT).text() or 1)
        except ValueError:
            raise ValueError("the error and the weight of a minimum must be numbers") from None
        if not w > 0:
            raise ValueError("the weight of a minimum must be positive")
        method = METHOD_CODES.get(t.item(r, METHOD).text().strip().lower())  # anything else: not stated
        if page.weight_by_method.isChecked():
            w *= weights_by_method([_WEIGHT_KEY.get(method)])[0]
        out.append(Minimum(float(t.item(r, TIME).text()), None if error is None else error / sqrt(w),
                           t.item(r, KIND).text(), t.item(r, SOURCE).text(), method))  # fmt: skip
    return out


def as_text(minima):
    """The minima as the text the oc_fit step parses (the background fit takes text)."""
    return "\n".join(
        f"{m.time!r} {'' if m.error is None else repr(m.error)} {m.kind} {m.method or ''} {m.source}".strip()
        for m in minima
    )

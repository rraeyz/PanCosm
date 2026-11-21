"""The Models window's Lower / Upper columns (plans/interface.md UI-16.6): the limits of a parameter, empty meaning
the engine's own. The values go to models.eb_fit as its `bounds`; the prior stays flat inside them (the MCMC engine
takes no per-parameter prior here)."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QTableWidgetItem

from ..models import fit
from .kit import tokens
from .messages import translate as translate_message

translate = QCoreApplication.translate
LOWER, UPPER = 3, 4


def header():
    return [translate("ModelsWindow", "Lower"), translate("ModelsWindow", "Upper")]


def add_items(table, row):
    for c in (LOWER, UPPER):
        table.setItem(row, c, QTableWidgetItem(""))


def texts(table, names):
    return tuple((table.item(r, LOWER).text(), table.item(r, UPPER).text()) for r in range(len(names)))


def set_texts(table, values):
    for r, (lo, hi) in enumerate(values):
        table.item(r, LOWER).setText(lo)
        table.item(r, UPPER).setText(hi)


def read(table, names):
    """{name: (lower or None, upper or None)} for the rows with a limit; ValueError when a cell is not a number."""
    out = {}
    for r, name in enumerate(names):
        cells = []
        for c in (LOWER, UPPER):
            text = table.item(r, c).text().strip()
            try:
                cells.append(float(text) if text else None)
            except ValueError:
                raise ValueError(translate("ModelsWindow", "Limit of {p} not understood.").format(
                    p=table.item(r, 0).text())) from None  # fmt: skip
        if cells != [None, None]:
            out[name] = tuple(cells)
    return out


def check(table, names, start, bounds):
    """Mark the rows whose start value is outside its limits; ValueError (the engine's message) for the first."""
    table.blockSignals(True)  # a colour is no edit: not an undo step
    brush, first = QBrush(QColor(tokens.role("non_linear"))), None
    for r, name in enumerate(names):
        item = table.item(r, 1)
        try:
            fit.check_start(start, {name: bounds[name]} if name in bounds else {})
            item.setBackground(QBrush())
            item.setToolTip("")
        except ValueError as e:
            item.setBackground(brush)
            item.setToolTip(translate_message(e))
            first = first or e
    table.blockSignals(False)
    if first:
        raise first

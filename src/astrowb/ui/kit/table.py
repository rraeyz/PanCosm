"""TableView: an Astropy Table shown without copying it into widgets, so a million rows open and scroll at once
(ARC-8). Sorting by a header click, a filter line in core/table.select's expressions, a column chooser, cells
coloured with their reason in a tooltip, copy and Export… in every core/table format.

    view = TableView(); view.set_table(table, marks={(row, "flux"): (tokens.ROLES["saturated"], "saturated")})
    view.row_chosen.connect(...)            # the row's index in the table, whatever the sort and filter
"""

import numpy as np
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ...core import table as T
from . import tokens


class _Model(QAbstractTableModel):
    edited = Signal(int, str, object, object)  # table row, column name, old value, new value

    def __init__(self):
        super().__init__()
        self.table, self.rows, self.marks, self.cache = None, np.arange(0), {}, {}
        self.editable = set()  # names of the columns a user may change
        self.numeric = set()  # names of the number columns: right-aligned, monospace
        self.errors = {}  # value column -> its error column: shown to the error's digits
        from ..theme import MONO

        self.mono = QFont(MONO)

    def flags(self, index):
        base = super().flags(index)
        if self.table is not None and self.table.colnames[index.column()] in self.editable:
            return base | Qt.ItemIsEditable
        return base

    def setData(self, index, value, role=Qt.EditRole):
        """A typed value checked by the column's kind: a number column takes numbers only (refused otherwise)."""
        if role != Qt.EditRole or not index.isValid():
            return False
        row, name = int(self.rows[index.row()]), self.table.colnames[index.column()]
        column = self.table[name]
        try:
            new = {"f": float, "i": int, "u": int, "b": lambda v: str(v).lower() in ("1", "true", "yes")}.get(
                column.dtype.kind, str
            )(str(value).strip().replace(",", ".") if column.dtype.kind in "fiu" else value)
        except ValueError:
            return False
        old = column[row].item() if hasattr(column[row], "item") else column[row]
        if new == old:
            return False
        self.set_value(row, name, new)
        self.edited.emit(row, name, old, new)
        return True

    def set_value(self, row, name, value):
        """Change one cell (also for undo / redo, without the edited signal)."""
        self.table[name][row] = value
        shown = np.flatnonzero(self.rows == row)
        if len(shown):
            i = self.index(int(shown[0]), self.table.colnames.index(name))
            self.dataChanged.emit(i, i)

    def rowCount(self, parent=QModelIndex()):  # noqa: B008
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):  # noqa: B008
        return 0 if parent.isValid() or self.table is None else len(self.table.colnames)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if self.table is None or role not in (Qt.DisplayRole, Qt.ToolTipRole):
            return None
        if orientation == Qt.Vertical:
            return str(int(self.rows[section]) + 1) if role == Qt.DisplayRole else None
        col = self.table.columns[section]
        if role == Qt.ToolTipRole:
            return col.description or None
        return f"{col.name} [{col.unit}]" if col.unit else col.name

    def data(self, index, role=Qt.DisplayRole):
        row, name = int(self.rows[index.row()]), self.table.colnames[index.column()]
        if role == Qt.DisplayRole and name in self.errors:  # digits by the error (UI-11): 12345.678 ± 12 → 12346
            shown = _by_error(self.table[name][row], self.table[self.errors[name]][row])
            if shown is not None:
                return shown
        if role in (Qt.DisplayRole, Qt.EditRole):
            return _text(self.table[name], row)
        if role == Qt.TextAlignmentRole:
            return int(Qt.AlignRight | Qt.AlignVCenter) if name in self.numeric else None
        if role == Qt.FontRole and name in self.numeric:
            return self.mono  # digits of one width: a column of numbers lines up
        mark = self.marks.get((row, name))
        if mark and role == Qt.BackgroundRole:
            return QColor(mark[0])
        if mark and role == Qt.ToolTipRole:
            return mark[1]
        return None


ERROR_SUFFIXES = ("_err", "_error", "_sigma", "_e")


def _errors(table):
    """{value column: its error column} for float columns with a partner named <name>_err (or _error, _sigma, _e)
    and no format of their own; an error column is shown by itself, to two significant digits."""
    out = {}
    for name in table.colnames:
        col = table[name]
        if col.dtype.kind != "f" or col.format:
            continue
        partner = next((name + s for s in ERROR_SUFFIXES if name + s in table.colnames), None)
        if partner is not None and table[partner].dtype.kind == "f":
            out[name] = partner
            out.setdefault(partner, partner)
    return out


def _by_error(value, error):
    """value with as many decimals as two significant digits of error need; None when either is not a number."""
    import math

    if not (np.isfinite(value) and np.isfinite(error)) or error <= 0:
        return None
    decimals = max(0, 1 - math.floor(math.log10(error)))
    return f"{value:.{decimals}f}"


def _text(column, row):
    v = column[row]
    if column.dtype.kind == "f":
        if not np.isfinite(v):
            return ""
        fmt = column.format
        # 15 digits: a BJD keeps its microdays, a sum keeps no float noise (0.1 + 0.2 shows 0.3)
        return (fmt.format(v) if "{" in fmt else format(v, fmt.lstrip("%"))) if fmt else f"{v:.15g}"
    return str(v)


class TableView(QWidget):
    row_chosen = Signal(int)  # the row's index in the table

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.filter = QLineEdit(self)
        self.filter.setPlaceholderText(self.tr("Filter, e.g. flux_err < 0.01 and not isnan(airmass)"))
        self.filter.setClearButtonEnabled(True)
        self.filter.returnPressed.connect(self._apply)
        self.filter.textChanged.connect(lambda text: None if text else self._apply())
        self.view = QTableView(self)
        self.model = _Model()
        self.view.setModel(self.model)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setAlternatingRowColors(True)
        self.view.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)  # no per-row size: a million rows
        self.view.verticalHeader().setDefaultSectionSize(self.fontMetrics().height() + 6)
        header = self.view.horizontalHeader()
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        header.sectionClicked.connect(self._sort_by)
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self._column_menu)
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self._menu)
        self.view.selectionModel().currentRowChanged.connect(
            lambda cur, _prev: cur.isValid() and self.row_chosen.emit(int(self.model.rows[cur.row()]))
        )
        self.count = QLabel(self)  # "12 of 48 rows · 2 selected"
        self.count.setProperty("muted", True)
        self.view.selectionModel().selectionChanged.connect(lambda *_: self._count())
        lay.addWidget(self.filter)
        lay.addWidget(self.view)
        lay.addWidget(self.count)
        self.sort = None  # (column name, ascending)

    def set_table(self, table, marks=None, editable=()):
        """Show a table (kept, not copied); marks: {(row index, column name): (colour, reason)}; editable: the
        columns a user may change (each change is the model's edited signal: an undo step for the window)."""
        self.model.beginResetModel()
        self.model.table, self.model.marks, self.model.editable = table, dict(marks or {}), set(editable)
        # found once: asked per cell and role, a column look-up made a million-row table open late
        self.model.numeric = {n for n in table.colnames if table[n].dtype.kind in "iuf"}
        self.model.errors = _errors(table)
        self.model.rows = np.arange(len(table))
        self.model.endResetModel()
        self._apply()

    def shown_rows(self):
        """Indices in the table of the rows shown, in their shown order."""
        return self.model.rows.copy()

    def selected_rows(self):
        return sorted(int(self.model.rows[i.row()]) for i in self.view.selectionModel().selectedRows())

    def _apply(self):
        """Filter, then sort, keeping the table itself untouched."""
        t = self.model.table
        if t is None:
            return
        try:
            keep = np.flatnonzero(T.select(t, self.filter.text()))
            self.filter.setToolTip(self.tr("{n} of {total} rows").format(n=len(keep), total=len(t)))
            self.filter.setStyleSheet("")
        except ValueError as e:
            from ..messages import translate

            self.filter.setToolTip(translate(str(e)))
            self.filter.setStyleSheet(f"QLineEdit {{ border: 1px solid {tokens.DARK['error']}; }}")
            return
        if self.sort is not None:
            name, ascending = self.sort
            values = np.asarray(t[name])[keep]
            if values.dtype.kind == "f":  # empty (NaN) last whichever way
                order = np.lexsort((values if ascending else -values, np.isnan(values)))
            else:
                order = np.argsort(values, kind="stable")
                order = order if ascending else order[::-1]
            keep = keep[order]
        self.model.beginResetModel()
        self.model.rows = keep
        self.model.endResetModel()
        self._count()

    def _count(self):
        t = self.model.table
        if t is None:
            self.count.setText("")
            return
        shown, total, chosen = len(self.model.rows), len(t), len(self.view.selectionModel().selectedRows())
        if not shown:  # an empty table says why (UI-11)
            empty = self.tr("No rows yet") if not total else self.tr("No row matches the filter ({n} rows in all)")
            self.count.setText(empty.format(n=total))
            return
        text = self.tr("{n} rows").format(n=total) if shown == total else self.tr("{n} of {total} rows").format(
            n=shown, total=total)  # fmt: skip
        self.count.setText(text + (self.tr(" · {n} selected").format(n=chosen) if chosen else ""))

    def _sort_by(self, section):
        name = self.model.table.colnames[section]
        self.sort_by(name, not (self.sort == (name, True)))

    def _column_menu(self, pos):
        self.column_menu(self.view.horizontalHeader().logicalIndexAt(pos)).exec(
            self.view.horizontalHeader().mapToGlobal(pos)
        )

    def column_menu(self, section):
        """The header's menu (UI-11): sort by the column clicked, fit its width, then show or hide each column."""
        menu = QMenu(self)
        if self.model.table is None:
            return menu
        if section >= 0:
            col = self.model.table.colnames[section]
            menu.addAction(self.tr("Sort ascending"), lambda c=col: self.sort_by(c, True))
            menu.addAction(self.tr("Sort descending"), lambda c=col: self.sort_by(c, False))
            menu.addAction(self.tr("Fit the width"), lambda: self.view.resizeColumnToContents(section))
            menu.addSeparator()
        for i, name in enumerate(self.model.table.colnames):
            act = menu.addAction(name)
            act.setCheckable(True)
            act.setChecked(not self.view.isColumnHidden(i))
            act.toggled.connect(lambda on, i=i: self.view.setColumnHidden(i, not on))
        return menu

    def sort_by(self, name, ascending=True):
        self.sort = (name, ascending)
        section = self.model.table.colnames.index(name)
        self.view.horizontalHeader().setSortIndicator(section, Qt.AscendingOrder if ascending else Qt.DescendingOrder)
        self._apply()

    def copy_text(self, rows=None):
        """Tab-separated text of the given table rows (default: the selected, else the shown) with the headers."""
        rows = self.selected_rows() or list(self.model.rows) if rows is None else rows
        cols = [i for i in range(self.model.columnCount()) if not self.view.isColumnHidden(i)]
        names = [self.model.table.colnames[i] for i in cols]
        lines = ["\t".join(str(self.model.headerData(i, Qt.Horizontal)) for i in cols)]
        lines += ["\t".join(_text(self.model.table[n], int(r)) for n in names) for r in rows]
        return "\n".join(lines)

    def export(self, path):
        """The shown rows (filter and sort applied) and columns to a file, by its extension."""
        t = self.model.table[self.model.rows]
        hidden = [n for i, n in enumerate(t.colnames) if self.view.isColumnHidden(i)]
        t.remove_columns(hidden)
        return T.write(t, path)

    def _menu(self, pos):
        menu = QMenu(self)
        menu.addAction(self.tr("Copy"), lambda: QApplication.clipboard().setText(self.copy_text()))
        menu.addAction(self.tr("Export…"), self._export_dialog)
        menu.exec(self.view.viewport().mapToGlobal(pos))

    def _export_dialog(self):
        kinds = self.tr("CSV (*.csv);;ECSV (*.ecsv);;VOTable (*.vot);;LaTeX (*.tex);;Markdown (*.md);;HTML (*.html)")
        path, _ = QFileDialog.getSaveFileName(self, self.tr("Export table"), "", kinds)
        if path:
            self.export(path)

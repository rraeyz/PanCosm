"""TableView: an Astropy Table shown without copying it into widgets, so a million rows open and scroll at once
(ARC-8). Sorting by a header click, a filter line in core/table.select's expressions, a column chooser, cells
coloured with their reason in a tooltip, copy and Export… in every core/table format.

    view = TableView(); view.set_table(table, marks={(row, "flux"): ("#ffcdd2", "saturated")})
    view.row_chosen.connect(...)            # the row's index in the table, whatever the sort and filter
"""

import numpy as np
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QHeaderView,
    QLineEdit,
    QMenu,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ...core import table as T


class _Model(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.table, self.rows, self.marks, self.cache = None, np.arange(0), {}, {}

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
        if role == Qt.DisplayRole:
            return _text(self.table[name], row)
        if role == Qt.TextAlignmentRole:
            return int(Qt.AlignRight | Qt.AlignVCenter) if self.table[name].dtype.kind in "iuf" else None
        mark = self.marks.get((row, name))
        if mark and role == Qt.BackgroundRole:
            return QColor(mark[0])
        if mark and role == Qt.ToolTipRole:
            return mark[1]
        return None


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
        lay.addWidget(self.filter)
        lay.addWidget(self.view)
        self.sort = None  # (column name, ascending)

    def set_table(self, table, marks=None):
        """Show a table (kept, not copied); marks: {(row index, column name): (colour, reason)}."""
        self.model.beginResetModel()
        self.model.table, self.model.marks = table, dict(marks or {})
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
            self.filter.setStyleSheet("QLineEdit { border: 1px solid #c62828; }")
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

    def _sort_by(self, section):
        name = self.model.table.colnames[section]
        ascending = not (self.sort == (name, True))
        self.sort = (name, ascending)
        self.view.horizontalHeader().setSortIndicator(section, Qt.AscendingOrder if ascending else Qt.DescendingOrder)
        self._apply()

    def _column_menu(self, pos):
        menu = QMenu(self)
        for i, name in enumerate(self.model.table.colnames if self.model.table is not None else []):
            act = menu.addAction(name)
            act.setCheckable(True)
            act.setChecked(not self.view.isColumnHidden(i))
            act.toggled.connect(lambda on, i=i: self.view.setColumnHidden(i, not on))
        menu.exec(self.view.horizontalHeader().mapToGlobal(pos))

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

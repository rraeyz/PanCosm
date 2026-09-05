"""One table component for every area window (plans/interface.md I2.6): sorting (numbers as numbers), a column
chooser, a filter, cells coloured with the reason in their tooltip, copy and CSV / LaTeX export, and a signal
telling the window which row (frame, star, line…) was chosen — as AstroImageJ's measurements table, inside the
window instead of a window of its own."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QLineEdit,
    QMenu,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class _Item(QTableWidgetItem):
    """Sorts numbers by value (10 after 9), text by text; empty cells last."""

    def __lt__(self, other):
        a, b = self.data(Qt.UserRole + 1), other.data(Qt.UserRole + 1)
        if a is not None and b is not None:
            return a < b
        if (a is None) != (b is None):
            return b is None
        return self.text() < other.text()


def _number(text):
    try:
        return float(str(text).replace("−", "-"))
    except ValueError:
        return None


class DataTable(QWidget):
    row_chosen = Signal(object)  # the key given with the row (a frame's path, a star's index…)

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.filter = QLineEdit(self)
        self.filter.setPlaceholderText(self.tr("Filter rows…"))
        self.filter.setToolTip(self.tr("Only rows that hold every word typed here are shown"))
        self.filter.setClearButtonEnabled(True)
        self.filter.textChanged.connect(self._apply_filter)
        self.table = QTableWidget(self)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setToolTip(
            self.tr("Click to sort; right-click to choose which columns are shown")
        )
        self.table.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.horizontalHeader().customContextMenuRequested.connect(self._column_menu)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._menu)
        self.table.currentCellChanged.connect(lambda row, *_: self._chosen(row))
        lay.addWidget(self.filter)
        lay.addWidget(self.table)

    def set_data(self, header, rows, keys=None):
        """header: column titles; rows: lists of values (numbers are sorted as numbers); keys: one per row, sent
        by row_chosen."""
        t = self.table
        t.setSortingEnabled(False)
        t.clear()
        t.setColumnCount(len(header))
        t.setHorizontalHeaderLabels([str(h) for h in header])
        t.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                item = _Item("" if value is None else str(value))
                item.setData(Qt.UserRole + 1, value if isinstance(value, (int, float)) else _number(item.text()))
                if c == 0:
                    item.setData(Qt.UserRole, None if keys is None else keys[r])
                t.setItem(r, c, item)
        t.setSortingEnabled(True)
        t.resizeColumnsToContents()
        self._apply_filter(self.filter.text())

    def key(self, row):
        item = self.table.item(row, 0)
        return None if item is None else item.data(Qt.UserRole)

    def mark(self, row, column, colour, reason):
        """Colour one cell and say why in its tooltip (a saturated star, a frame left out, a poor fit)."""
        item = self.table.item(row, column)
        if item is not None:
            item.setBackground(QColor(colour))
            item.setToolTip(reason)

    def _chosen(self, row):
        if row >= 0:
            self.row_chosen.emit(self.key(row))

    def _apply_filter(self, text):
        words = text.casefold().split()
        t = self.table
        for r in range(t.rowCount()):
            cells = " ".join(t.item(r, c).text().casefold() for c in range(t.columnCount()) if t.item(r, c))
            t.setRowHidden(r, not all(w in cells for w in words))

    def _column_menu(self, pos):
        menu = QMenu(self)
        header = self.table.horizontalHeader()
        for c in range(self.table.columnCount()):
            item = self.table.horizontalHeaderItem(c)
            act = menu.addAction(item.text() if item else str(c + 1))
            act.setCheckable(True)
            act.setChecked(not self.table.isColumnHidden(c))
            act.toggled.connect(lambda on, col=c: self.table.setColumnHidden(col, not on))
        menu.popup(header.mapToGlobal(pos))
        return menu

    def _menu(self, pos):
        from .export import export_table, selected_text, table_rows

        menu = QMenu(self)
        copy = menu.addAction(self.tr("Copy"))
        copy.setEnabled(bool(self.table.selectedIndexes()))
        copy.triggered.connect(lambda: QApplication.clipboard().setText(selected_text(self.table)))
        whole = menu.addAction(self.tr("Copy table"))

        def copy_all():
            header, rows = table_rows(self.table)
            QApplication.clipboard().setText("\n".join("\t".join(r) for r in [header, *rows]))

        whole.triggered.connect(copy_all)
        export = menu.addAction(self.tr("Export table (CSV or LaTeX)…"))

        def export_to():
            path, _ = QFileDialog.getSaveFileName(
                self, self.tr("Export table"), "table.csv", "CSV (*.csv);;LaTeX (*.tex)"
            )
            if path:
                export_table(self.table, path)

        export.triggered.connect(export_to)
        menu.popup(self.table.viewport().mapToGlobal(pos))
        return menu

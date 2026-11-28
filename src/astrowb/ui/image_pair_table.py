"""The "Pairs" results tab of the Images window (plans/photometry.md PHO-24): each two-star measurement the Line tool
made can be added as a row, then exported as CSV / ECSV (the table's Export…)."""

import numpy as np
from astropy.table import Table
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from .image_pair import pair_of, pair_rows_of
from .kit.table import TableView

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("Ctx", "…") calls

# pair_measure's own keys and their units ("" = none); the sky keys exist only with a WCS
COLUMNS = {
    "x1": "pix", "y1": "pix", "x2": "pix", "y2": "pix", "separation_px": "pix", "separation_arcsec": "arcsec",
    "position_angle": "deg", "ratio": "", "ratio_err": "", "dmag": "mag", "dmag_err": "mag",
    "r_ap": "pix", "r_in": "pix", "r_out": "pix",
}  # fmt: skip


class PairTable(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pairs = []  # the measurements added (dicts as pair_measure returns them)
        self.last = None  # the latest measurement, waiting for "Add to table"
        self.table = TableView(self)
        self.table.set_row_actions([(self.tr("Delete"), self.delete)])
        self.add_button = QPushButton(self.tr("Add to table"), self)
        self.add_button.clicked.connect(self.add)
        self.delete_button = QPushButton(self.tr("Delete"), self)
        self.delete_button.clicked.connect(lambda: self.delete(self.table.selected_rows()))
        self.export_button = QPushButton(self.tr("Export…"), self)
        self.export_button.clicked.connect(self.table._export_dialog)
        self.add_button.setToolTip(self.tr("Keep the latest measured pair as a row of the table"))
        self.delete_button.setToolTip(self.tr("Take the selected pairs out of the table"))
        self.export_button.setToolTip(self.tr("Save the table as CSV or ECSV"))
        row = QHBoxLayout()
        for b in (self.add_button, self.delete_button, self.export_button):
            row.addWidget(b)
        row.addStretch(1)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(row)
        lay.addWidget(self.table)
        self.set_last(None)

    def set_last(self, pair):
        self.last = pair
        self.add_button.setEnabled(pair is not None)

    def add(self):
        if self.last is not None:
            self.pairs.append(self.last)
            self._show()

    def delete(self, rows):
        self.pairs = [p for i, p in enumerate(self.pairs) if i not in set(rows)]
        self._show()

    def _show(self):
        t = Table()
        for name, unit in COLUMNS.items():
            if any(name in p for p in self.pairs):
                t[name] = np.array([p.get(name, np.nan) for p in self.pairs], dtype=float)
                t[name].unit = unit or None
        self.table.set_table(t)


def show_pair(page, data, x0, y0, x1, y1):
    """The Line tool's pair rows for the Information tab; also keeps the pair for the page's Pairs tab."""
    p = pair_of(data, x0, y0, x1, y1, page.wcs)
    pairs = getattr(page, "pair_table", None)
    if p is not None and pairs is None:
        pairs = page.pair_table = PairTable(page)
        page.tabs.addTab(pairs, translate("ImagePage", "Pairs"))
    if pairs is not None:
        pairs.set_last(p)
    return pair_rows_of(p)

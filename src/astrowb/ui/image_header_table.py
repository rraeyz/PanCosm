"""The Images window's FITS keyword table (UI-11)."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QHeaderView, QTableWidget

from .kit.table_view import DataTable

translate = QCoreApplication.translate


def header_frame(page):
    """A DataTable whose cells the page fills and edits through its keyword dialog."""
    frame = DataTable(page)
    frame.prepare(
        [translate("ImagePage", "Keyword"), translate("ImagePage", "Value"), translate("ImagePage", "Comment")]
    )
    head = frame.table.horizontalHeader()
    head.setSectionResizeMode(QHeaderView.Interactive)
    head.setStretchLastSection(True)
    frame.table.setEditTriggers(QTableWidget.NoEditTriggers)
    frame.table.cellDoubleClicked.connect(lambda _row, _col: page.edit_keyword_dialog())
    frame.table.setToolTip(
        translate(
            "ImagePage", "Double-click a keyword to change it; drag a column's edge to widen it; right-click to copy"
        )
    )
    return frame

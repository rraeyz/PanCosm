"""The right panel of details (plans/interface.md "The component kit", UI-3): key–value rows with units, selectable
text, and Copy for the whole panel.

    panel = Inspector(self.tr("Star"))
    panel.set_rows([(self.tr("Flux"), 12345.6, "ADU"), (self.tr("FWHM"), 3.2, "px")])
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QFormLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


def _text(value):
    if isinstance(value, float):
        return f"{value:.15g}"  # a BJD keeps its microdays (as in kit/table.py)
    return "" if value is None else str(value)


class Inspector(QWidget):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        head = QHBoxLayout()
        self.title = QLabel(f"<b>{title}</b>", self)
        self.copy_button = QPushButton(self.tr("Copy"), self)
        self.copy_button.setFlat(True)
        self.copy_button.clicked.connect(lambda: QApplication.clipboard().setText(self.copy_text()))
        head.addWidget(self.title, 1)
        head.addWidget(self.copy_button)
        lay.addLayout(head)
        self.form = QFormLayout()
        self.form.setLabelAlignment(Qt.AlignLeft)
        lay.addLayout(self.form)
        lay.addStretch(1)
        self.rows = []

    def set_title(self, title):
        self.title.setText(f"<b>{title}</b>")

    def set_rows(self, rows):
        """rows: [(name, value, unit or "")]; numbers in the monospace font."""
        while self.form.rowCount():
            self.form.removeRow(0)
        self.rows = [(row[0], row[1], row[2] if len(row) > 2 else "") for row in rows]
        from ..theme import MONO

        mono = QFont(MONO, self.font().pointSize())
        for name, value, unit in self.rows:
            label = QLabel(f"{_text(value)} {unit}".strip(), self)
            label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
            if isinstance(value, int | float):
                label.setFont(mono)
            key = QLabel(name, self)
            key.setProperty("muted", True)
            self.form.addRow(key, label)

    def copy_text(self):
        return "\n".join(f"{name}\t{_text(value)}\t{unit}".rstrip() for name, value, unit in self.rows)

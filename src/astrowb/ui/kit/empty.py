"""What a view shows while it has no data (plans/interface.md "The component kit", UI-3; every view gets one in
UI-6): what the view will show, the first action, and "Try with practice data" when there is a sample.

    EmptyState("open", self.tr("No images yet"), self.tr("Open FITS files to look at them and measure stars."),
               (self.tr("Open images…"), self.open_files), sample=self.open_practice_data)
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class EmptyState(QWidget):
    def __init__(self, icon, title, text, primary, secondary=None, sample=None, parent=None):
        super().__init__(parent)
        from .icons import icon as kit_icon

        lay = QVBoxLayout(self)
        lay.addStretch(1)
        picture = QLabel(self)
        picture.setPixmap(kit_icon(icon, self, 48).pixmap(48, 48))
        self.title = QLabel(f"<b>{title}</b>", self)
        self.text = QLabel(text, self)
        self.text.setWordWrap(True)
        self.text.setProperty("muted", True)
        self.buttons = []
        for i, action in enumerate(a for a in (primary, secondary) if a):
            name, slot = action
            b = QPushButton(name, self)
            b.clicked.connect(slot)
            b.setDefault(i == 0)
            self.buttons.append(b)
        if sample is not None:
            b = QPushButton(self.tr("Try with practice data"), self)
            b.setFlat(True)
            b.clicked.connect(sample)
            self.buttons.append(b)
        for w in (picture, self.title, self.text, *self.buttons):
            w.setMaximumWidth(420)
            lay.addWidget(w, 0, Qt.AlignHCenter)
        self.text.setAlignment(Qt.AlignHCenter)
        self.text.setMinimumWidth(min(420, self.text.fontMetrics().horizontalAdvance(text) + 8))  # wraps past 420
        lay.addStretch(2)

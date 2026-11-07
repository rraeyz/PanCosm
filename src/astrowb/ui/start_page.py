"""The start page: entry points from whatever data the user already has."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from ..brand import BRAND
from .widgets import _title


class StartPage(QWidget):
    """Entry points: the user starts from whatever data they already have."""

    action = Signal(str)  # "new_project" | "open_project" | "open_fits" | workspace key
    mode_chosen = Signal(str)  # "basic" | "expert"

    def __init__(self, parent=None, mode="basic"):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.addWidget(_title(self.tr("Welcome to {app}").format(app=BRAND.display_name), self))
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Interface:"), self), 0, Qt.AlignTop)
        modes = QVBoxLayout()  # one under the other: side by side wider than a small window
        self.basic = QRadioButton(self.tr("Basic — the main steps; the rarely changed options folded"), self)
        self.expert = QRadioButton(self.tr("Expert — every option open"), self)
        tip = self.tr(
            "Nothing is removed in Basic mode: the folded sections open with one click. Change it here or in the "
            "Settings menu at any time."
        )
        for b, key in ((self.basic, "basic"), (self.expert, "expert")):
            b.setToolTip(tip)
            b.toggled.connect(lambda on, k=key: self.mode_chosen.emit(k) if on else None)
            modes.addWidget(b)
        (self.expert if mode == "expert" else self.basic).setChecked(True)
        row.addLayout(modes)
        row.addStretch(1)
        lay.addLayout(row)
        lay.addWidget(QLabel(self.tr("Start from what you have:"), self))
        self.grid = grid = QGridLayout()
        self.buttons, self.columns = [], 0
        entries = [
            (self.tr("New project"), self.tr("Keep frames, settings and results together"), "new_project"),
            (self.tr("Open project…"), self.tr("Continue earlier work"), "open_project"),
            (self.tr("Open a FITS image"), self.tr("Look at an image and its header"), "open_fits"),
            (self.tr("I have raw frames"), self.tr("Calibrate with bias, dark and flat"), "calibrate"),
            (self.tr("I have calibrated images"), self.tr("Measure brightness of stars"), "photometry"),
            (self.tr("I have spectra"), self.tr("Reduce spectra, measure radial velocities"), "spectroscopy"),
            (self.tr("I have minima or RV lists"), self.tr("O-C diagrams, orbits"), "timeseries"),
            (self.tr("I want to plan a night"), self.tr("Visibility, airmass, targets"), "plan"),
        ]
        for title, hint, key in entries:
            button = QPushButton(f"{title}\n{hint}", self)
            button.setMinimumHeight(56)
            button.setObjectName(f"start_{key}")
            button.setToolTip(hint)
            button.clicked.connect(lambda _=False, k=key: self.action.emit(k))
            self.buttons.append(button)
        self._arrange(1)
        lay.addLayout(grid)
        lay.addStretch(1)

    def _arrange(self, columns):
        """Two columns of buttons where they fit, one on a narrow window."""
        if columns != self.columns:
            self.columns = columns
            for i, button in enumerate(self.buttons):
                self.grid.addWidget(button, i // columns, i % columns)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        widest = max(b.minimumSizeHint().width() for b in self.buttons)
        margins = self.layout().contentsMargins()
        room = event.size().width() - margins.left() - margins.right()
        self._arrange(2 if room >= 2 * widest + self.grid.horizontalSpacing() else 1)

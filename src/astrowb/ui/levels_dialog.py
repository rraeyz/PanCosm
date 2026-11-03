"""Screen stretch as in MaxIm DL / PixInsight: the image's histogram with the black and white levels, colour maps
and an inverted display. Only the picture on screen changes, never the data."""

import numpy as np
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ..display import COLOUR_MAPS, display_limits


class LevelsDialog(QDialog):
    def __init__(self, viewer, parent=None):
        from .workspaces import PlotCanvas

        super().__init__(parent)
        self.viewer = viewer
        self.setWindowTitle(self.tr("Display levels and colours"))
        self.resize(560, 460)
        lay = QVBoxLayout(self)
        self.plot = PlotCanvas(self)
        lay.addWidget(self.plot, 1)
        grid = QGridLayout()
        self.black, self.white = QDoubleSpinBox(self), QDoubleSpinBox(self)
        for w in (self.black, self.white):
            w.setRange(-1e12, 1e12)
            w.setDecimals(2)
            w.setKeyboardTracking(False)
            w.valueChanged.connect(self._apply)
        grid.addWidget(QLabel(self.tr("Black level"), self), 0, 0)
        grid.addWidget(self.black, 0, 1)
        grid.addWidget(QLabel(self.tr("White level"), self), 1, 0)
        grid.addWidget(self.white, 1, 1)
        auto = QPushButton(self.tr("Automatic (from the interval)"), self)
        auto.clicked.connect(self.automatic)
        grid.addWidget(auto, 0, 2, 2, 1)
        names = {
            "grey": self.tr("Grey"),
            "heat": self.tr("Heat"),
            "viridis": "Viridis",
            "inferno": "Inferno",
            "magma": "Magma",
            "cividis": "Cividis",
            "cool": self.tr("Cool"),
            "rainbow": self.tr("Rainbow"),
        }
        self.cmap = QComboBox(self)
        for key in COLOUR_MAPS:
            self.cmap.addItem(names[key], key)
        self.cmap.setCurrentIndex(self.cmap.findData(viewer.cmap))
        self.cmap.currentIndexChanged.connect(self._apply)
        grid.addWidget(QLabel(self.tr("Colours"), self), 2, 0)
        grid.addWidget(self.cmap, 2, 1)
        self.invert = QCheckBox(self.tr("Inverted (black stars on white)"), self)
        self.invert.setChecked(viewer.invert)
        self.invert.toggled.connect(self._apply)
        grid.addWidget(self.invert, 2, 2)
        lay.addLayout(grid)
        self._lines = []
        self.refresh()

    def refresh(self):
        """Histogram of the current image (a regular sample of at most a million pixels) and its levels."""
        data = self.viewer.data
        if data is None:
            return
        from ..display import _sample

        sample = _sample(data)
        lo, hi = self.viewer.limits or display_limits(data, self.viewer.interval)
        a, b = np.percentile(sample, (0.05, 99.95)) if sample.size else (0.0, 1.0)
        a, b = min(a, lo), max(b, hi)
        self.plot.figure.clear()
        ax = self.plot.figure.add_subplot()
        ax.hist(sample, bins=256, range=(a, b if b > a else a + 1), color="#8e8e93")
        ax.set_yscale("log")
        ax.set_xlabel(self.tr("Pixel value"))
        ax.set_ylabel(self.tr("Number of pixels"))
        self._lines = [ax.axvline(v, color=c, lw=1.2) for v, c in ((lo, "#3e63dd"), (hi, "#e5484d"))]
        self.plot.draw()
        for w, v in ((self.black, lo), (self.white, hi)):
            w.blockSignals(True)
            w.setValue(v)
            w.blockSignals(False)

    def automatic(self):
        self.viewer.set_levels(None)
        self.refresh()

    def _apply(self, *_):
        lo, hi = self.black.value(), self.white.value()
        limits = (lo, hi) if hi > lo else None
        self.viewer.set_levels(limits, self.cmap.currentData(), self.invert.isChecked())
        for line, v in zip(self._lines, (lo, hi), strict=False):
            line.set_xdata([v, v])
        self.plot.draw()

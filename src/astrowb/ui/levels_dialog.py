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
from .kit import tokens
from .plot.spec import AxisSpec, FigureSpec, PanelSpec, SeriesSpec


class LevelsDialog(QDialog):
    def __init__(self, viewer, parent=None):
        from .plot.toolbar import PlotToolbar  # pyqtgraph is imported when a plot is first needed
        from .plot.view import PlotView

        super().__init__(parent)
        self.viewer = viewer
        self.setWindowTitle(self.tr("Display levels and colours"))
        self.resize(560, 460)
        lay = QVBoxLayout(self)
        self.plot = PlotView(parent=self)
        lay.addWidget(PlotToolbar(self.plot, self))
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
        self.white.setToolTip(
            self.tr(
                "Pixel value shown as white; higher values are white too. Only the display changes, never the data."
            )
        )
        self.black.setToolTip(self.tr("Pixel value shown as black; lower values are black too"))
        auto = QPushButton(self.tr("Automatic (from the interval)"), self)
        auto.clicked.connect(self.automatic)
        auto.setToolTip(
            self.tr("Black and white levels chosen from the image (zscale or the interval set in the View menu)")
        )
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
        self.cmap.setToolTip(
            self.tr(
                "Colour table of the display; grey is best for judging faint detail, others make small "
                "differences stand out"
            )
        )
        grid.addWidget(QLabel(self.tr("Colours"), self), 2, 0)
        grid.addWidget(self.cmap, 2, 1)
        self.invert = QCheckBox(self.tr("Inverted (black stars on white)"), self)
        self.invert.setChecked(viewer.invert)
        self.invert.toggled.connect(self._apply)
        self.invert.setToolTip(
            self.tr(
                "Black stars on a white sky, as on photographic plates and finding charts; faint objects "
                "are often easier to see"
            )
        )
        grid.addWidget(self.invert, 2, 2)
        lay.addLayout(grid)
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
        counts, edges = np.histogram(sample, bins=256, range=(a, b if b > a else a + 1))
        # shortcut: empty bins sit at 0.5 so the log axis can draw them; exact counts are in the data copy otherwise
        series = [
            SeriesSpec(
                self.tr("Number of pixels"),
                edges[:-1],
                np.maximum(counts, 0.5),
                kind="steps",
                colour=tokens.role("rejected"),
            ),
            SeriesSpec(self.tr("Black level"), [lo], kind="vline", colour=tokens.role("check")),
            SeriesSpec(self.tr("White level"), [hi], kind="vline", colour=tokens.role("saturated")),
        ]
        axes = AxisSpec(self.tr("Pixel value")), AxisSpec(self.tr("Number of pixels"), scale="log")
        self.plot.set_figure(FigureSpec([PanelSpec(*axes, series)]))
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
        self.plot.move_vline(self.tr("Black level"), lo)
        self.plot.move_vline(self.tr("White level"), hi)

"""Variable-star search tab (as Muniwin's varfind): every star of the field measured on every frame, the
magnitude-scatter diagram with the candidates marked, and any star's light curve one click away."""

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .workspaces import PlotCanvas

FITS = "FITS (*.fits *.fit *.fts *.FITS *.FIT)"


class VarFindPage(QWidget):
    search_requested = Signal(list, dict)  # images, params
    light_curve_chosen = Signal(list, list, str)  # time, relative flux, label (to the Period search tab)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.images, self.result, self.star = [], None, None
        split = QSplitter(Qt.Horizontal, self)
        left = QWidget(self)
        lay = QVBoxLayout(left)
        info = QLabel(
            self.tr(
                "Measures every star of the first frame on all frames, puts them on a common zero point (clouds "
                "cancel) and compares each star's scatter with stars of the same brightness. Stars well above "
                "the magnitude–scatter relation are candidates. Use calibrated frames."
            ),
            self,
        )
        info.setWordWrap(True)
        lay.addWidget(info)
        choose = QPushButton(self.tr("Choose frames…"), self)
        choose.clicked.connect(
            lambda: self.set_images(QFileDialog.getOpenFileNames(self, self.tr("Frames"), "", FITS)[0])
        )
        lay.addWidget(choose)
        self.source = QLabel(self.tr("No frames."), self)
        lay.addWidget(self.source)
        form = QFormLayout()
        self.method = QComboBox(self)
        self.method.addItem(self.tr("Aperture photometry"), "aperture")
        self.method.addItem(self.tr("PSF photometry (crowded fields)"), "psf")
        self.max_stars = QSpinBox(self)
        self.max_stars.setRange(10, 5000)
        self.max_stars.setValue(300)
        self.threshold = QDoubleSpinBox(self)
        self.threshold.setRange(1, 50)
        self.threshold.setValue(3.0)
        self.threshold.setToolTip(self.tr("How far above the typical scatter (in its own spread) a candidate must be"))
        form.addRow(self.tr("Photometry"), self.method)
        form.addRow(self.tr("Brightest stars to measure"), self.max_stars)
        form.addRow(self.tr("Candidate threshold (σ)"), self.threshold)
        lay.addLayout(form)
        self.button = QPushButton(self.tr("Search for variables"), self)
        self.button.setEnabled(False)
        self.button.clicked.connect(self._search)
        lay.addWidget(self.button)
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(
            [self.tr("x"), self.tr("y"), self.tr("Magnitude"), self.tr("rms (mag)"), self.tr("Index")]
        )
        self.table.cellClicked.connect(lambda r, _c: self.show_star(int(self.table.item(r, 0).data(Qt.UserRole))))
        lay.addWidget(self.table, 1)
        self.send = QPushButton(self.tr("Send this star to Period search"), self)
        self.send.setEnabled(False)
        self.send.clicked.connect(self._send)
        lay.addWidget(self.send)
        split.addWidget(left)
        self.plot = PlotCanvas(self)
        self.plot.canvas.mpl_connect("button_press_event", self._clicked)
        split.addWidget(self.plot)
        split.setSizes([420, 800])
        QVBoxLayout(self).addWidget(split)

    def set_images(self, paths):
        self.images = list(paths)
        self.source.setText(self.tr("{n} frames").format(n=len(self.images)))
        self.button.setEnabled(len(self.images) >= 5)

    def _search(self):
        self.result = None
        self.status.setText(self.tr("Measuring every star…"))
        params = {
            "max_stars": self.max_stars.value(),
            "method": self.method.currentData(),
            "threshold": self.threshold.value(),
        }
        self.search_requested.emit(self.images, params)

    def show_result(self, out):
        self.result = out
        v = out["variability"]
        xy = np.asarray(out["field"]["xy"])
        cand = np.flatnonzero(v["candidate"])
        order = cand[np.argsort(-np.asarray(v["index"])[cand])]
        self.table.setRowCount(len(order))
        for r, j in enumerate(order):
            for c, value in enumerate((xy[j, 0], xy[j, 1], v["mean"][j], v["rms"][j], v["index"][j])):
                item = QTableWidgetItem(f"{value:.4g}")
                item.setData(Qt.UserRole, int(j))
                self.table.setItem(r, c, item)
        self.status.setText(self.tr("{n} stars measured, {m} candidates.").format(n=len(xy), m=len(order)))
        self.show_star(int(order[0]) if len(order) else None)

    def show_star(self, j):
        self.star = j
        v = self.result["variability"]
        mean, rms = np.asarray(v["mean"]), np.asarray(v["rms"])
        cand = np.asarray(v["candidate"])
        self.plot.figure.clear()
        ax1, ax2 = self.plot.figure.subplots(2, 1)
        ax1.plot(mean, rms, ".", ms=4, color="C0")
        ax1.plot(mean[cand], rms[cand], "o", ms=6, mfc="none", color="C3")
        order = np.argsort(mean)
        ax1.plot(mean[order], np.asarray(v["typical"])[order], lw=0.8, color="C1")
        ax1.set_yscale("log")
        ax1.set_xlabel(self.tr("Instrumental magnitude"))
        ax1.set_ylabel(self.tr("rms (mag)"))
        self._scatter_ax = ax1
        if j is not None:
            ax1.plot(mean[j], rms[j], "*", ms=12, color="C2")
            t = np.asarray(self.result["field"]["time"])
            m = np.asarray(v["corrected"])[:, j]
            ax2.plot(t - np.floor(t.min()), m, ".", ms=3)
            ax2.invert_yaxis()
            ax2.set_xlabel(self.tr("JD − {d:.0f}").format(d=np.floor(t.min())))
            ax2.set_ylabel(self.tr("Magnitude"))
        self.send.setEnabled(j is not None)
        self.plot.draw()

    def _clicked(self, event):
        if self.result is None or event.inaxes is not getattr(self, "_scatter_ax", None) or event.ydata is None:
            return
        v = self.result["variability"]
        mean, rms = np.asarray(v["mean"]), np.log10(np.maximum(np.asarray(v["rms"]), 1e-6))
        (x0, x1), (y0, y1) = event.inaxes.get_xlim(), np.log10(np.maximum(event.inaxes.get_ylim(), 1e-6))
        d = np.hypot((mean - event.xdata) / (x1 - x0), (rms - np.log10(max(event.ydata, 1e-6))) / (y1 - y0))
        d[~np.isfinite(d)] = np.inf
        self.show_star(int(np.argmin(d)))

    def _send(self):
        if self.star is None:
            return
        v = self.result["variability"]
        t = np.asarray(self.result["field"]["time"])
        m = np.asarray(v["corrected"])[:, self.star]
        ok = np.isfinite(m)
        x, y = self.result["field"]["xy"][self.star]
        flux = 10 ** (-0.4 * (m[ok] - np.nanmedian(m)))
        self.light_curve_chosen.emit(
            t[ok].tolist(), flux.tolist(), self.tr("star at x={x:.0f} y={y:.0f}").format(x=x, y=y)
        )

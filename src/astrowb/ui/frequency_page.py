"""Frequency analysis tab (as Period04): amplitude spectrum, spectral window, prewhitening,
multi-frequency fit and times of maximum, on the light curve of the Period search tab."""

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
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

FREQ_COLUMNS = ("freq", "freq_err", "period", "amp", "amp_err", "phase", "phase_err", "snr")


class FrequencyPage(QWidget):
    analyse_requested = Signal(list, list, dict)  # time, flux, params

    def __init__(self, period_page, parent=None):
        super().__init__(parent)
        self.period_page = period_page  # the light curve (and its edits) lives there
        self.result = None
        split = QSplitter(Qt.Horizontal, self)
        left = QWidget(self)
        lay = QVBoxLayout(left)
        info = QLabel(
            self.tr(
                "Uses the light curve of the Period search tab. The highest peak of the amplitude spectrum is "
                "fitted, removed (prewhitening) and the search repeated until the next peak has S/N below the "
                "limit (Breger: 4). All frequencies, amplitudes and phases are refitted together."
            ),
            self,
        )
        info.setWordWrap(True)
        lay.addWidget(info)
        form = QFormLayout()
        self.f_max = QDoubleSpinBox(self)
        self.f_max.setRange(0.01, 10000)
        self.f_max.setDecimals(3)
        self.f_max.setValue(50.0)
        self.n_max = QSpinBox(self)
        self.n_max.setRange(1, 100)
        self.n_max.setValue(10)
        self.snr_min = QDoubleSpinBox(self)
        self.snr_min.setRange(1, 100)
        self.snr_min.setValue(4.0)
        self.magnitudes = QCheckBox(self.tr("Values are magnitudes (maximum = brightest = smallest)"), self)
        form.addRow(self.tr("Highest frequency (c/d)"), self.f_max)
        form.addRow(self.tr("At most this many frequencies"), self.n_max)
        form.addRow(self.tr("Stop below S/N"), self.snr_min)
        lay.addLayout(form)
        lay.addWidget(self.magnitudes)
        self.clean = QCheckBox(self.tr("Also show the CLEANed spectrum (the sampling's aliases removed)"), self)
        self.clean.setToolTip(self.tr("Roberts, Lehár & Dreher (1987); slower on long series"))
        lay.addWidget(self.clean)
        self.button = QPushButton(self.tr("Analyse frequencies"), self)
        self.button.clicked.connect(self._analyse)
        lay.addWidget(self.button)
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.status)
        self.table = QTableWidget(0, len(FREQ_COLUMNS), self)
        self.table.setHorizontalHeaderLabels(
            [
                self.tr("Frequency (c/d)"),
                self.tr("σ"),
                self.tr("Period (d)"),
                self.tr("Amplitude"),
                self.tr("σ"),
                self.tr("Phase"),
                self.tr("σ"),
                self.tr("S/N"),
            ]
        )
        lay.addWidget(self.table, 2)
        lay.addWidget(QLabel(self.tr("Times of maximum"), self))
        self.maxima = QTableWidget(0, 2, self)
        self.maxima.setHorizontalHeaderLabels([self.tr("Time"), self.tr("σ (d)")])
        lay.addWidget(self.maxima, 1)
        self.to_oc = QPushButton(self.tr("Send maxima to the O-C diagram"), self)
        self.to_oc.setEnabled(False)
        lay.addWidget(self.to_oc)
        split.addWidget(left)
        self.plot = PlotCanvas(self)
        split.addWidget(self.plot)
        split.setSizes([420, 800])
        QVBoxLayout(self).addWidget(split)

    def _analyse(self):
        if not self.period_page.time or len(self.period_page.time) < 10:
            self.status.setText(self.tr("Load a light curve on the Period search tab first."))
            return
        self.result = None
        self.status.setText(self.tr("Analysing…"))
        params = {
            "f_max": self.f_max.value(),
            "n_max": self.n_max.value(),
            "snr_min": self.snr_min.value(),
            "magnitudes": self.magnitudes.isChecked(),
            "clean": self.clean.isChecked(),
        }
        self.analyse_requested.emit(list(self.period_page.time), list(self.period_page.flux), params)

    def show_result(self, out):
        self.result = out
        rows = out["frequencies"]
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            values = dict(row, period=1 / row["freq"])
            for c, key in enumerate(FREQ_COLUMNS):
                self.table.setItem(r, c, QTableWidgetItem(f"{values[key]:.6g}"))
        self.maxima.setRowCount(len(out["maxima"]))
        for r, (tm, err) in enumerate(out["maxima"]):
            self.maxima.setItem(r, 0, QTableWidgetItem(f"{tm:.6f}"))
            self.maxima.setItem(r, 1, QTableWidgetItem(f"{err:.6f}"))
        self.to_oc.setEnabled(bool(out["maxima"]))
        if rows:
            self.status.setText(self.tr("{n} frequencies; residual rms {rms:.4g}").format(n=len(rows), rms=out["rms"]))
        else:
            self.status.setText(self.tr("No peak above the S/N limit."))
        grid = np.asarray(out["grid"])
        self.plot.figure.clear()
        ax1, ax2, ax3 = self.plot.figure.subplots(3, 1, sharex=True)
        ax1.plot(grid, out["spectrum"], lw=0.6, label=self.tr("amplitude spectrum"))
        if out.get("clean_spectrum"):
            ax1.plot(grid, out["clean_spectrum"], lw=0.8, color="C2", label=self.tr("CLEAN"))
            ax1.legend(loc="upper right", fontsize="small")
        for row in rows:
            ax1.axvline(row["freq"], color="r", lw=0.6, alpha=0.6)
        ax1.set_ylabel(self.tr("Amplitude"))
        ax2.plot(grid, out["residual_spectrum"], lw=0.6)
        ax2.plot(grid, self.snr_min.value() * _running_mean(np.asarray(out["residual_spectrum"]), grid), lw=0.8)
        ax2.set_ylabel(self.tr("Residuals"))
        ax3.plot(grid, out["window"], lw=0.6)
        ax3.set_ylabel(self.tr("Window"))
        ax3.set_xlabel(self.tr("Frequency (c/d)"))
        self.plot.draw()


def _running_mean(amp, grid, box=2.0):
    """Breger's noise level (mean amplitude within +-1 c/d) along the spectrum, for the S/N line."""
    df = grid[1] - grid[0] if grid.size > 1 else 1.0
    k = max(1, min(amp.size, int(box / df)))
    return np.convolve(np.pad(amp, k // 2, mode="edge"), np.ones(k) / k, mode="valid")[: amp.size]

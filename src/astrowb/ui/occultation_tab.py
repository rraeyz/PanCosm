"""The Light curves window's Occultation tab (PHO-38): a light curve, the square-well fit of the step
`timeseries.occultation`, the fit and its errors in a table and the model over the data."""

from pathlib import Path

import numpy as np
from astropy.table import Table
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .kit.table import TableView
from .messages import translate
from .plot.spec import AxisSpec, FigureSpec, PanelSpec, SeriesSpec
from .plot.view import PlotView

LOAD_ERRORS = (OSError, ValueError, KeyError, IndexError, TypeError)


class OccultationTab(QWidget):
    """Load a light curve, fit the occultation, read the times with their errors."""

    fit_requested = Signal(list, list)  # time, flux: the window runs the step and calls show_result / show_error

    def __init__(self, parent=None):
        super().__init__(parent)
        self.time = self.flux = self.result = None
        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        self.load_button = QPushButton(self.tr("Load light curve…"), self)
        self.load_button.setToolTip(
            self.tr("A CSV file or a light-curve file (.lc.ecsv) with an evenly sampled series")
        )
        self.load_button.clicked.connect(self._load)
        self.fit_button = QPushButton(self.tr("Fit the occultation"), self)
        self.fit_button.setToolTip(
            self.tr("Fits a square well (a drop with sharp edges) and gives the disappearance and reappearance times")
        )
        self.fit_button.clicked.connect(self._fit)
        row.addWidget(self.load_button)
        row.addWidget(self.fit_button)
        lay.addLayout(row)
        self.status = QLabel(self.tr("No light curve yet: load a file."), self)
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        self.plot = PlotView(FigureSpec([]), parent=self)
        self.table = TableView(self)
        lay.addWidget(self.plot, 3)
        lay.addWidget(self.table, 1)

    def _load(self, path=None):
        """path: a file given by the caller; otherwise (a button click) asked."""
        if not isinstance(path, str):
            path, _ = QFileDialog.getOpenFileName(
                self, self.tr("Load light curve"), "", "CSV (*.csv *.txt *.dat);;Light-curve file (*.lc.ecsv *.ecsv)"
            )
        if not path:
            return
        from ..models.data import read_light_curve

        try:
            t, flux, _err, _ = read_light_curve(path)
        except LOAD_ERRORS as e:
            return self.show_error(
                self.tr("Cannot read {file}: {error}").format(file=Path(path).name, error=translate(e))
            )
        self.time, self.flux, self.result = t.tolist(), flux.tolist(), None
        self.status.setText(self.tr("{file}: {n} points").format(file=Path(path).name, n=len(t)))
        self._plot()

    def _fit(self):
        if self.time is None:
            return self.show_error(self.tr("Load a light curve first."))
        self.fit_requested.emit(self.time, self.flux)

    def show_error(self, message):
        self.status.setText(translate(message))

    def show_result(self, out):
        self.result = fit = out["occultation"]
        rows = [
            (self.tr("Disappearance time D"), fit["D"], fit["D_err"]),
            (self.tr("Reappearance time R"), fit["R"], fit["R_err"]),
            (self.tr("Duration"), fit["duration"], fit["duration_err"]),
            (self.tr("Magnitude drop"), fit["mag_drop"] if fit["mag_drop"] is not None else np.nan, np.nan),
            (self.tr("Flux outside"), fit["base"], np.nan),
            (self.tr("Flux inside"), fit["bottom"], np.nan),
        ]
        names, values, errors = zip(*rows, strict=True)
        self.table.set_table(Table({"quantity": names, "value": values, "error": errors}))
        self.status.setText(self.tr("Fitted: the times are in the unit of the light curve's time column."))
        self._plot()

    def _plot(self):
        t = np.asarray(self.time)
        series = [SeriesSpec(self.tr("light curve"), t, self.flux, size=3, alpha=0.8)]
        if self.result:
            from ..photometry.occultation import _model

            f = self.result
            dt = float(np.median(np.diff(t)))
            series.append(
                SeriesSpec(
                    self.tr("model"), t, _model(t, dt, f["D"], f["R"], f["base"], f["bottom"]), kind="line", width=2
                )
            )
        self.plot.set_figure(
            FigureSpec(
                [PanelSpec(AxisSpec(self.tr("Time")), AxisSpec(self.tr("Relative flux")), series)], shared_x=False
            )
        )

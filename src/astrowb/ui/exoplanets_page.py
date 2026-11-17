"""The Exoplanets page (plans/interface.md UI-16.7): a saved light curve (the Photometry window's .lc.ecsv, or a CSV of
time, flux, error) fitted with photometry.transit_fit. The controls are the step's own parameters, grouped as the
window's stages (Data, Star, Planets, Model, Fit, Uncertainty, Results); the main view is the transit and its
residuals."""

from pathlib import Path

import numpy as np
from PySide6.QtCore import QCoreApplication, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from . import photometry_transit as transit
from .exoplanets_density import density_line
from .kit.table_view import DataTable
from .messages import translate as message
from .plot.toolbar import plot_box

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("ExoplanetsPage", "…") calls
STAGES = ("data", "star", "planets", "model", "fit", "uncertainty", "results")


def read_light_curve(path):
    """The light-curve dict of a .lc.ecsv file, or of a CSV / text table of time, flux, error."""
    from ..photometry import lcfile

    if lcfile.is_lcfile(path):
        return lcfile.read(path)
    first = Path(path).read_text(encoding="utf-8", errors="replace").lstrip()[:1]
    data = np.genfromtxt(
        path, delimiter="," if str(path).endswith(".csv") else None, skip_header=0 if first.isdigit() else 1
    )
    if data.ndim != 2 or data.shape[1] < 3 or len(data) < 10:
        raise ValueError("a light curve needs at least 10 rows of time, flux and error")
    return {"time": data[:, 0].tolist(), "rel_flux": data[:, 1].tolist(), "rel_flux_err": data[:, 2].tolist()}


class ExoplanetsPage(QWidget):
    fit_requested = Signal(dict, dict)  # step inputs, params
    stage_done = Signal(str)  # a stage key: the rail gets its tick
    midtimes_to_oc = Signal(list)  # [(file, Tc, σ)] for the O−C window

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sets, self.fits, self.current = [], {}, 0  # (name, light curve) per file; the fit of each; the chosen one
        self.left = QWidget(self)  # stages_from_boxes wants the column the controls came from; there is none
        self.left.hide()
        self.stage_boxes = {key: QWidget(self) for key in STAGES}
        self.forms = {key: QFormLayout() for key in STAGES}
        for key, box in self.stage_boxes.items():
            QVBoxLayout(box).setContentsMargins(0, 0, 0, 0)
            box.layout().addLayout(self.forms[key])

        self.table = DataTable(self)
        self.table.row_chosen.connect(self._choose)
        self.stage_boxes["data"].layout().insertWidget(0, self.table)
        self.open_button = QPushButton(translate("ExoplanetsPage", "Open light curves…"), self)
        self.open_button.setToolTip(
            translate("ExoplanetsPage", "Light-curve files from Photometry (.lc.ecsv), or tables of time, flux, error")
        )
        self.open_button.clicked.connect(lambda: self.add_files(None))
        self.stage_boxes["data"].layout().insertWidget(1, self.open_button)
        self.u1 = self._add("star", translate("ExoplanetsPage", "Limb darkening u1"), self._spin(0.4, -1, 2, 3),
                      translate("ExoplanetsPage", "Quadratic law of the star; fixed unless chosen to fit"))  # fmt: skip
        self.u2 = self._add(
            "star", translate("ExoplanetsPage", "Limb darkening u2"), self._spin(0.2, -1, 2, 3), self.u1.toolTip()
        )
        self.fit_ld = self._add("star", "", QCheckBox(translate("ExoplanetsPage", "Fit the limb darkening"), self),
                          translate("ExoplanetsPage", "A single night rarely decides it: leave it fixed"))  # fmt: skip
        self._planets()
        self._model_and_fit()
        self._main_view()

    def _planets(self):
        self.period = self._add("planets", translate("ExoplanetsPage", "Period (d)"), self._spin(1.0, 0.01, 10000, 7),
                          translate("ExoplanetsPage", "Fixed for a single transit"))  # fmt: skip
        self.tc = self._add("planets", translate("ExoplanetsPage", "Mid-transit"), self._spin(0, 0, 1e8, 6, True),
                      translate("ExoplanetsPage", "Start value; auto: the dip of the curve"))  # fmt: skip
        self.k = self._add("planets", translate("ExoplanetsPage", "Rp/R★"), self._spin(0, 0, 0.5, 4, True),
                     translate("ExoplanetsPage", "Start value; auto: the square root of the depth"))  # fmt: skip
        self.a_rs = self._add(
            "planets",
            translate("ExoplanetsPage", "a/R★"),
            self._spin(8, 1, 1000, 3),
            translate("ExoplanetsPage", "Start value"),
        )
        self.b = self._add(
            "planets",
            translate("ExoplanetsPage", "Impact parameter"),
            self._spin(0.3, 0, 1.5, 3),
            translate("ExoplanetsPage", "Start value"),
        )

    def _model_and_fit(self):
        self.detrend = self._add(
            "model",
            translate("ExoplanetsPage", "Detrend against"),
            QLineEdit("airmass", self),
            translate("ExoplanetsPage", "Comma-separated: airmass, fwhm, sky, x, y (empty: none)"),
        )
        self.fit_button = QPushButton(translate("ExoplanetsPage", "Fit the transit"), self)
        self.fit_button.setToolTip(
            translate("ExoplanetsPage", "Fits the chosen light curve; Stop is in the status bar")
        )
        self.fit_button.clicked.connect(self.fit)
        self.stage_boxes["fit"].layout().insertWidget(0, self.fit_button)
        self.red_noise = self._add(
            "uncertainty",
            "",
            QCheckBox(translate("ExoplanetsPage", "Account for red noise (errors × β)"), self),
            translate("ExoplanetsPage", "The errors multiplied by β, the time-averaging factor of the residuals"),
        )
        self.mcmc = self._add(
            "uncertainty",
            translate("ExoplanetsPage", "MCMC steps"),
            QSpinBox(self),
            translate("ExoplanetsPage", "Posterior errors after the fit (stops earlier once converged); 0: none"),
        )
        self.mcmc.setRange(0, 100000)
        self.mcmc.setSingleStep(1000)
        self.exoclock_button = QPushButton(translate("ExoplanetsPage", "ExoClock file…"), self)
        self.etd_button = QPushButton(translate("ExoplanetsPage", "ETD file…"), self)
        self.exoclock_button.setToolTip(translate("ExoplanetsPage", "Time, normalised flux, error in BJD_TDB"))
        self.etd_button.setToolTip(translate("ExoplanetsPage", "Julian date, magnitude, error, for the ETD"))
        self.expected_rho = self._add(
            "results",
            translate("ExoplanetsPage", "Expected ρ★ (from the star)"),
            self._spin(0, 0, 100, 3, True),
            translate("ExoplanetsPage", "g/cm³; if set, the stellar-density line says how many σ apart"),
        )
        self.expected_rho.valueChanged.connect(self._density)
        for b in (self.exoclock_button, self.etd_button):
            self.stage_boxes["results"].layout().addWidget(b)
        self.exoclock_button.clicked.connect(lambda: self.export("exoclock"))
        self.etd_button.clicked.connect(lambda: self.export("etd"))
        for box in self.stage_boxes.values():
            box.layout().addStretch(1)

    def _main_view(self):
        lay = QVBoxLayout(self)
        box, self.plot = plot_box(self)
        lay.addWidget(box, 3)
        self.values = DataTable(self)
        lay.addWidget(self.values, 2)
        self.result = QLabel(translate("ExoplanetsPage", "Open a light curve to begin."), self)
        self.result.setWordWrap(True)
        self.result.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.result)

    def _add(self, key, label, widget, tip=""):
        widget.setToolTip(tip)
        self.forms[key].addRow(label, widget)
        return widget

    def _spin(self, value, lo, hi, decimals, auto=False):
        s = QDoubleSpinBox(self)
        s.setRange(lo, hi)
        s.setDecimals(decimals)
        s.setValue(value)
        if auto:
            s.setSpecialValueText(translate("ExoplanetsPage", "auto"))
        return s

    # --- data ----------------------------------------------------------------
    def add_files(self, paths):
        paths = (
            paths
            or QFileDialog.getOpenFileNames(
                self,
                translate("ExoplanetsPage", "Open light curves"),
                "",
                "Light curves (*.lc.ecsv *.ecsv *.csv *.txt *.dat);;*",
            )[0]
        )
        errors = []
        for path in paths:
            try:
                lc = read_light_curve(str(path))
            except (OSError, ValueError, KeyError) as e:
                errors.append(
                    translate("ExoplanetsPage", "Cannot read {file}: {error}").format(
                        file=Path(path).name, error=message(e)
                    )
                )
                continue
            self.sets.append((Path(path).name, lc))
        rows = [[n, len(lc["time"]), round(float(np.ptp(lc["time"])), 4), lc.get("time_scale", "")]
                for n, lc in self.sets]  # fmt: skip
        header = [
            translate("ExoplanetsPage", "File"),
            translate("ExoplanetsPage", "Points"),
            translate("ExoplanetsPage", "Time span (d)"),
            translate("ExoplanetsPage", "Time scale"),
        ]
        self.table.set_data(header, rows, list(range(len(rows))))
        if self.sets:
            self.table.table.selectRow(len(self.sets) - 1)
            self.stage_done.emit("data")
        if errors:  # after the table: choosing its row shows that fit's text
            self.result.setText("\n".join(errors))

    def _choose(self, i):
        self.current = i
        if i in self.fits:
            self.show_fit(self.fits[i])

    # --- fit -----------------------------------------------------------------
    def fit(self):
        if not self.sets:
            self.result.setText(translate("ExoplanetsPage", "Open a light curve first."))
            return
        lc = self.sets[self.current][1]
        t0, k0 = transit.starts(lc)
        params = {"period": self.period.value(), "tc": self.tc.value() or t0, "k": self.k.value() or k0,
                  "a_rs": self.a_rs.value(), "b": self.b.value(), "u1": self.u1.value(), "u2": self.u2.value(),
                  "detrend": self.detrend.text(), "fit_ld": self.fit_ld.isChecked(),
                  "red_noise": self.red_noise.isChecked(), "mcmc_steps": self.mcmc.value()}  # fmt: skip
        self.result.setText(translate("ExoplanetsPage", "Fitting the transit…"))
        self.fit_requested.emit({"light_curve": lc}, params)

    def show_fit(self, out):
        out = out.get("transit", out)
        self.fits[self.current] = out
        self.plot.set_figure(transit.transit_figure(self.sets[self.current][1], out))
        header = [
            translate("ExoplanetsPage", "Parameter"),
            translate("ExoplanetsPage", "Value"),
            translate("ExoplanetsPage", "Error"),
        ]
        self.values.set_data(header, transit.parameter_rows(out))
        self.result.setText(transit.result_text(out))
        self._density()
        for key in ("fit", "results"):
            self.stage_done.emit(key)

    def _density(self):
        out = self.fits.get(self.current)
        if out is None or out.get("eclipse"):
            return
        self.result.setText(
            transit.result_text(out) + "\n" + density_line(out, self.period.value(), self.expected_rho.value())
        )

    def export(self, kind, path=None):
        """The ExoClock or ETD upload file of the chosen light curve."""
        from ..photometry.reports import etd, exoclock

        if not self.sets:
            self.result.setText(translate("ExoplanetsPage", "Open a light curve first."))
            return None
        lc = self.sets[self.current][1]
        name = "ExoClock.txt" if kind == "exoclock" else "ETD.txt"
        path = path or QFileDialog.getSaveFileName(self, translate("ExoplanetsPage", "Save"), name, "Text (*.txt)")[0]
        if not path:
            return None
        try:
            if kind == "exoclock":
                exoclock.write(lc, path, self.fits.get(self.current))
            else:
                Path(path).write_text(etd.etd_text(lc)[0], encoding="utf-8")
        except (ValueError, OSError) as e:
            self.result.setText(message(e))
            return None
        self.result.setText(translate("ExoplanetsPage", "Saved {name}").format(name=path))
        return path

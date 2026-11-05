"""Spectrum tools tab (as IRAF splot, BASS, ISIS): measure lines, V/R, arithmetic, smoothing,
continuum, instrument response, series of equivalent widths, BeSS / ARAS export."""

from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .messages import translate
from .undo import Undoable
from .workspaces import PlotCanvas

SPECTRA = "Spectra (*.fits *.fit *.fts *.txt *.dat *.csv *.asc)"
LINE_COLUMNS = ("file", "centre", "fwhm", "ew", "ew_err", "ew_fit", "depth", "line_flux", "snr", "v_over_r")


def _spin(parent, value, lo, hi, decimals=2):
    w = QDoubleSpinBox(parent)
    w.setRange(lo, hi)
    w.setDecimals(decimals)
    w.setValue(value)
    return w


class SpectrumToolsTab(Undoable, QWidget):
    atmosphere_requested = Signal(dict, dict)  # inputs (spectrum, optional solar spectrum), params

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_undo()
        self.wave = self.flux = self.header = None
        self.history, self.b, self.resp, self.points, self.last = [], None, None, [], None
        self.path = ""
        split = QSplitter(Qt.Horizontal, self)
        panel = QWidget(self)
        lay = QVBoxLayout(panel)

        opn = QPushButton(self.tr("Open spectrum…"), self)
        opn.clicked.connect(lambda: self._open())
        opn.setToolTip(
            self.tr(
                "A wavelength-calibrated 1-D spectrum: FITS (table or wavelength WCS) or a text file of "
                "wavelength and flux"
            )
        )
        self.source = QLabel(self.tr("No spectrum."), self)
        self.source.setWordWrap(True)
        lay.addWidget(opn)
        lay.addWidget(self.source)
        marks = QGridLayout()
        self.markers = QCheckBox(self.tr("Show line markers"), self)
        self.markers.toggled.connect(lambda _: self._plot())
        self.markers.setToolTip(
            self.tr("Marks common stellar lines (Balmer, Na D, Mg b, Ca II…) on the plot to help identify them")
        )
        self.marker_rv = _spin(self, 0.0, -5000, 5000, 1)
        self.marker_rv.setToolTip(self.tr("Shift the markers by this radial velocity (km/s)"))
        self.marker_rv.valueChanged.connect(lambda _: self.markers.isChecked() and self._plot())
        marks.addWidget(self.markers, 0, 0)
        marks.addWidget(self.marker_rv, 0, 1)
        lay.addLayout(marks)

        box = QGroupBox(self.tr("Measure a line"), self)
        g = QGridLayout(box)
        self.lo, self.hi = _spin(self, 6540, 0, 1e6), _spin(self, 6585, 0, 1e6)
        self.profile = QComboBox(self)
        self.profile.addItem(self.tr("Gaussian"), "gauss")
        self.profile.addItem(self.tr("Voigt"), "voigt")
        self.profile.setToolTip(
            self.tr("Gaussian for most lines; Voigt for strong lines with broad wings (Balmer lines, Na D)")
        )
        self.hi.setToolTip(
            self.tr(
                "Wavelength window of the line, with some continuum on both sides; or drag across the line on the plot"
            )
        )
        self.lo.setToolTip(
            self.tr(
                "Wavelength window of the line, with some continuum on both sides; or drag across the line on the plot"
            )
        )
        measure = QPushButton(self.tr("Measure"), self)
        measure.clicked.connect(self._measure)
        measure.setToolTip(
            self.tr(
                "Equivalent width, centre, FWHM and depth of the line from a profile fitted over a straight"
                " continuum at the window's edges"
            )
        )
        g.addWidget(QLabel(self.tr("From / to (Å) — or drag on the plot"), self), 0, 0, 1, 2)
        g.addWidget(self.lo, 1, 0)
        g.addWidget(self.hi, 1, 1)
        g.addWidget(self.profile, 2, 0)
        g.addWidget(measure, 2, 1)
        self.vr_centre = _spin(self, 6562.80, 0, 1e6)
        self.vr_half = _spin(self, 15.0, 0.1, 1000)
        self.vr_half.setToolTip(
            self.tr("The violet peak is searched below the centre and the red one above it, within this half width")
        )
        self.vr_centre.setToolTip(self.tr("Rest wavelength of the emission line, e.g. 6562.80 for Hα"))
        vr = QPushButton(self.tr("V/R"), self)
        vr.setToolTip(self.tr("Violet / red emission peaks of a normalised spectrum: (I_V − 1) / (I_R − 1)"))
        vr.clicked.connect(self._vr)
        g.addWidget(QLabel(self.tr("Line centre, ± half width (Å)"), self), 3, 0, 1, 2)
        g.addWidget(self.vr_centre, 4, 0)
        g.addWidget(self.vr_half, 4, 1)
        g.addWidget(vr, 5, 0)
        series = QPushButton(self.tr("Measure in several spectra…"), self)
        series.setToolTip(self.tr("The same window in many spectra: EW (and V/R) against date, e.g. Hα of a Be star"))
        series.clicked.connect(self._series)
        g.addWidget(series, 5, 1)
        lay.addWidget(box)

        box = QGroupBox(self.tr("Change the spectrum"), self)
        g = QGridLayout(box)
        self.smooth_kind = QComboBox(self)
        for text, key in (
            (self.tr("Gaussian (FWHM px)"), "gauss"),
            (self.tr("Boxcar (px)"), "boxcar"),
            (self.tr("Median (px)"), "median"),
        ):
            self.smooth_kind.addItem(text, key)
            self.smooth_kind.setToolTip(
                self.tr(
                    "Gaussian: lowers the resolution like a poorer spectrograph; boxcar: a running mean; "
                    "median: removes spikes and keeps edges"
                )
            )
        self.smooth_width = _spin(self, 3, 1, 999, 1)
        self.smooth_width.setToolTip(self.tr("Width of the smoothing in pixels"))
        smooth = QPushButton(self.tr("Smooth"), self)
        smooth.clicked.connect(self._smooth)
        smooth.setToolTip(self.tr("Smooths the spectrum (Undo takes it back)"))
        g.addWidget(self.smooth_kind, 0, 0)
        g.addWidget(self.smooth_width, 0, 1)
        g.addWidget(smooth, 0, 2)
        self.op = QComboBox(self)
        self.op.addItems(["+", "−", "×", "÷"])
        self.op.setToolTip(
            self.tr("Operation with a number or with spectrum B (e.g. divide by a standard star's spectrum)")
        )
        self.constant = QLineEdit(self)
        self.constant.setPlaceholderText(self.tr("number, or empty for spectrum B"))
        self.constant.setToolTip(self.tr("A number; empty: spectrum B, resampled onto this spectrum's wavelengths"))
        arith = QPushButton(self.tr("Apply"), self)
        arith.clicked.connect(self._arith)
        arith.setToolTip(self.tr("Applies the operation to the spectrum (Undo takes it back)"))
        open_b = QPushButton(self.tr("Spectrum B…"), self)
        open_b.clicked.connect(self._open_b)
        open_b.setToolTip(self.tr("A second spectrum for the operation with two spectra"))
        g.addWidget(self.op, 1, 0)
        g.addWidget(self.constant, 1, 1)
        g.addWidget(arith, 1, 2)
        g.addWidget(open_b, 2, 2)
        self.step = _spin(self, 1.0, 0.001, 1000, 3)
        self.step.setToolTip(self.tr("Step of the new, even wavelength grid in Å"))
        resample = QPushButton(self.tr("Resample (Å step)"), self)
        resample.clicked.connect(self._resample)
        resample.setToolTip(
            self.tr(
                "Puts the spectrum on an even wavelength grid with this step by linear interpolation "
                "(needed by some programs and archives)"
            )
        )
        g.addWidget(self.step, 2, 1)
        g.addWidget(resample, 2, 0)
        auto = QPushButton(self.tr("Normalise (automatic)"), self)
        auto.clicked.connect(self._normalise)
        auto.setToolTip(
            self.tr(
                "Divides by a smooth curve through the top of the spectrum (absorption lines left out); "
                "check the result, or pick the points yourself"
            )
        )
        self.pick = QPushButton(self.tr("Pick continuum points"), self)
        self.pick.setCheckable(True)
        self.pick.setToolTip(self.tr("Click continuum points on the plot, then press Normalise through points"))
        through = QPushButton(self.tr("Normalise through points"), self)
        through.clicked.connect(self._normalise_points)
        through.setToolTip(self.tr("Divides by a spline through the continuum points you clicked"))
        g.addWidget(auto, 3, 0)
        g.addWidget(self.pick, 3, 1)
        g.addWidget(through, 3, 2)
        response = QPushButton(self.tr("Instrument response…"), self)
        response.setToolTip(
            self.tr(
                "The open spectrum is a reference star; choose its known flux distribution (e.g. a Pickles spectrum)"
            )
        )
        response.clicked.connect(self._response)
        self.apply_resp = QPushButton(self.tr("Divide by response"), self)
        self.apply_resp.setEnabled(False)
        self.apply_resp.clicked.connect(self._apply_response)
        self.apply_resp.setToolTip(
            self.tr(
                "Divides the open spectrum by the instrument response measured from a reference star: relative fluxes"
            )
        )
        undo = QPushButton(self.tr("Undo"), self)
        undo.clicked.connect(self._undo)
        undo.setToolTip(self.tr("Takes back the last change of the spectrum"))
        g.addWidget(response, 4, 0)
        g.addWidget(self.apply_resp, 4, 1)
        g.addWidget(undo, 4, 2)
        save = QPushButton(self.tr("Save as…"), self)
        save.clicked.connect(lambda: self._save())
        save.setToolTip(self.tr("Saves the spectrum as it is now, as FITS or text"))
        bess = QPushButton(self.tr("Export for BeSS / ARAS…"), self)
        bess.clicked.connect(lambda: self._bess())
        bess.setToolTip(
            self.tr(
                "A FITS file in the format of the BeSS database and ARAS (header keywords they ask for, "
                "even wavelength grid)"
            )
        )
        g.addWidget(save, 5, 0)
        g.addWidget(bess, 5, 1, 1, 2)
        lay.addWidget(box)

        box = QGroupBox(self.tr("Stellar parameters (FGK stars)"), self)
        g = QGridLayout(box)
        self.resolution = QSpinBox(self)
        self.resolution.setRange(0, 500000)
        self.resolution.setSingleStep(1000)
        self.resolution.setSpecialValueText(self.tr("give R"))
        self.resolution.setToolTip(self.tr("Resolving power R = λ / Δλ of the spectrograph (FWHM of an arc line)"))
        g.addWidget(QLabel(self.tr("Resolution R"), self), 0, 0)
        g.addWidget(self.resolution, 0, 1)
        self.sun_file = QLineEdit(self)
        self.sun_file.setPlaceholderText(self.tr("solar spectrum, same spectrograph (optional)"))
        self.sun_file.setToolTip(
            self.tr(
                "The Sun observed with the same spectrograph (twilight sky, the Moon, an asteroid) makes the best "
                "reference; without it the Kurucz solar atlas is used."
            )
        )
        sun_pick = QPushButton(self.tr("Browse…"), self)
        sun_pick.setToolTip(self.tr("Choose the file in a dialog"))
        sun_pick.clicked.connect(
            lambda: self.sun_file.setText(
                QFileDialog.getOpenFileName(self, self.tr("Solar spectrum"), "", SPECTRA)[0] or self.sun_file.text()
            )
        )
        g.addWidget(self.sun_file, 1, 0)
        g.addWidget(sun_pick, 1, 1)
        atm = QPushButton(self.tr("Find Teff, log g, [Fe/H], v sin i"), self)
        atm.setToolTip(
            self.tr(
                "Fits synthetic spectra (PHOENIX, downloaded as needed) to the open spectrum, using only the "
                "wavelengths where the models reproduce the Sun, and gives the result relative to the Sun."
            )
        )
        atm.clicked.connect(self._atmosphere)
        g.addWidget(atm, 2, 0, 1, 2)
        lay.addWidget(box)
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.status)
        lay.addStretch(1)
        scroll = QScrollArea(self)
        scroll.setWidget(panel)
        scroll.setWidgetResizable(True)
        split.addWidget(scroll)

        right = QSplitter(Qt.Vertical, self)
        self.plot = PlotCanvas(self)
        self.plot.canvas.mpl_connect("button_press_event", self._clicked)
        right.addWidget(self.plot)
        self.table = QTableWidget(0, len(LINE_COLUMNS), self)
        self.table.setHorizontalHeaderLabels(
            [
                self.tr("File / date"),
                self.tr("Centre (Å)"),
                self.tr("FWHM (Å)"),
                self.tr("EW (Å)"),
                self.tr("σ EW"),
                self.tr("EW of fit"),
                self.tr("Depth"),
                self.tr("Line flux"),
                self.tr("S/N"),
                self.tr("V/R"),
            ]
        )
        right.addWidget(self.table)
        right.setSizes([600, 200])
        split.addWidget(right)
        split.setSizes([430, 800])
        QVBoxLayout(self).addWidget(split)

    # --- stellar parameters ----------------------------------------------------
    def _atmosphere(self):
        if self.wave is None:
            self.status.setText(self.tr("Open a spectrum first."))
            return
        if not self.resolution.value():
            self.status.setText(self.tr("Give the spectrograph's resolution R first."))
            return
        path = self.path
        if self.history:  # changed here (cleaned, cut, ...): the fit uses what is shown
            import tempfile

            from ..spectroscopy import spectrum_io

            path = str(Path(tempfile.mkdtemp()) / Path(self.path).name)
            spectrum_io.write(path, self.wave, self.flux, np.full_like(self.flux, np.nan), self.header)
        inputs = {"spectrum": path} | ({"sun": self.sun_file.text()} if self.sun_file.text().strip() else {})
        self.status.setText(self.tr("Fitting stellar parameters (the first time, model spectra are downloaded)…"))
        self.atmosphere_requested.emit(inputs, {"resolution": self.resolution.value()})

    def show_atmosphere(self, o):
        e = o["errors"]
        text = self.tr(
            "Teff = {t:.0f} ± {et:.0f} K, log g = {g:.2f} ± {eg:.2f}, [Fe/H] = {z:+.2f} ± {ez:.2f}, "
            "v sin i = {v:.1f} ± {ev:.1f} km/s, RV = {rv:.2f} ± {erv:.2f} km/s. Relative to the Sun fitted the same "
            "way; {pct:.0f} % of the pixels used (where the models reproduce the Sun); χ²ᵣ = {chi:.2f}."
        ).format(
            t=o["teff"], et=e["teff"], g=o["logg"], eg=e["logg"], z=o["feh"], ez=e["feh"], v=o["vsini"],
            ev=e["vsini"], rv=o["rv"], erv=e["rv"], pct=100 * o["used_fraction"], chi=o["chi2_red"],
        )  # fmt: skip
        if o["far_from_sun"]:
            text += " " + self.tr("This star is far from the Sun: the solar reference is less reliable here.")
        if o["at_edge"]:
            text += " " + self.tr("The fit stopped at the edge of the model grid.")
        text += " " + self.tr("So far checked on the Sun only; see the guide before publishing.")
        self.status.setText(text)
        self.plot.figure.clear()
        ax = self.plot.figure.subplots()
        p = o["plot"]
        ax.plot(p["wave"], p["flux"], lw=0.6, color="k", label=self.tr("observed"))
        ax.plot(p["wave"], p["model"], lw=0.6, color="C3", label=self.tr("model"))
        ax.set_xlabel(self.tr("Wavelength (Å)"))
        ax.legend(fontsize=8)
        self.plot.draw()

    # --- data ----------------------------------------------------------------
    def _read(self, path):
        from ..spectroscopy import spectrum_io

        try:
            return spectrum_io.read(path)
        except (OSError, ValueError, IndexError) as e:
            self.status.setText(self.tr("Cannot read {file}: {error}").format(file=Path(path).name, error=translate(e)))
            return None

    def _open(self, path=None):
        path = path or QFileDialog.getOpenFileName(self, self.tr("Open spectrum"), "", SPECTRA)[0]
        if not path:
            return False
        got = self._read(path)
        if got is None:
            return False
        self.wave, self.flux, _, self.header = got
        self.wave, self.flux = np.asarray(self.wave, float), np.asarray(self.flux, float)
        self.path, self.history, self.points, self.last = path, [], [], None
        self.undo_stack.clear()  # another spectrum: earlier steps do not apply to it
        self.source.setText(
            self.tr("{file}: {n} points, {a:.1f}–{b:.1f} Å").format(
                file=Path(path).name, n=self.wave.size, a=self.wave.min(), b=self.wave.max()
            )
        )
        self._plot()
        return True

    def _open_b(self, path=None):
        path = path or QFileDialog.getOpenFileName(self, self.tr("Spectrum B"), "", SPECTRA)[0]
        got = self._read(path) if path else None
        if got:
            self.b = (np.asarray(got[0], float), np.asarray(got[1], float))
            self.status.setText(self.tr("Spectrum B: {file}").format(file=Path(path).name))

    # --- undo / redo (Edit menu, Ctrl+Z / Ctrl+Y) -----------------------------
    def undo_state(self):
        return {"wave": self.wave, "flux": self.flux, "points": tuple(self.points)}

    def set_undo_state(self, state):
        self.wave, self.flux, self.points = state["wave"], state["flux"], list(state["points"])
        self.last = None
        self._plot()

    def _change(self, flux, what, step=None):
        self.edit(step or what.rstrip("."), self._set_flux, flux, what)

    def _set_flux(self, flux, what):
        self.history.append(self.flux)  # marks the spectrum as changed here (the stellar-parameter fit uses it)
        self.flux = np.asarray(flux, float)
        self.status.setText(what)
        self.last = None
        self._plot()

    def _ready(self):
        if self.wave is None:
            self.status.setText(self.tr("Open a spectrum first."))
            return False
        return True

    # --- plot ----------------------------------------------------------------
    def _plot(self):
        from matplotlib.widgets import SpanSelector

        from ..spectroscopy.analysis import C_KMS, LINES

        self.plot.figure.clear()
        ax = self.plot.figure.subplots()
        self.ax = ax
        if self.wave is not None:
            ax.plot(self.wave, self.flux, lw=0.7)
            if self.last:
                ax.plot(self.last["wave"], self.last["continuum"], "--", lw=0.8, color="C2")
                ax.plot(self.last["wave"], self.last["model"], lw=0.9, color="C3")
            for p in self.points:
                ax.axvline(p, color="C1", lw=0.6, ls=":")
            if self.markers.isChecked():
                shift = 1 + self.marker_rv.value() / C_KMS
                lo, hi = self.wave.min(), self.wave.max()
                for name, lam in LINES.items():
                    if lo <= lam * shift <= hi:
                        ax.axvline(lam * shift, color="gray", lw=0.5, alpha=0.7)
                        ax.text(
                            lam * shift,
                            1.0,
                            name,
                            rotation=90,
                            va="top",
                            ha="right",
                            fontsize=7,
                            transform=ax.get_xaxis_transform(),
                            color="gray",
                        )
        ax.set_xlabel(self.tr("Wavelength (Å)"))
        ax.set_ylabel(self.tr("Flux"))
        self._span = SpanSelector(
            ax, self._selected, "horizontal", useblit=True, minspan=0.1, props={"alpha": 0.2, "facecolor": "C1"}
        )
        self.plot.draw()

    def _selected(self, a, b):
        if not self.pick.isChecked():
            self.lo.setValue(min(a, b))
            self.hi.setValue(max(a, b))

    def _clicked(self, event):
        if self.pick.isChecked() and event.inaxes is not None and event.xdata is not None:
            self.edit(self.tr("pick a continuum point"), self._add_point, float(event.xdata))

    def _add_point(self, x):
        self.points.append(x)
        self._plot()

    # --- measurements --------------------------------------------------------
    def _add_row(self, label, m):
        r = self.table.rowCount()
        self.table.insertRow(r)
        for c, key in enumerate(LINE_COLUMNS):
            v = label if key == "file" else m.get(key)
            text = v if isinstance(v, str) else ("" if v is None else f"{v:.5g}")
            self.table.setItem(r, c, QTableWidgetItem(text))

    def _measure(self):
        from ..spectroscopy.analysis import measure_line

        if not self._ready():
            return None
        try:
            m = measure_line(self.wave, self.flux, self.lo.value(), self.hi.value(), self.profile.currentData())
        except (ValueError, RuntimeError) as e:
            self.status.setText(translate(e))
            return None
        self.last = m
        self._add_row(Path(self.path).name, m)
        text = self.tr(
            "Centre {c:.3f} ± {ce:.3f} Å, FWHM {f:.3f} Å, EW {ew:.4f} ± {ee:.4f} Å (fit {ef:.4f}), S/N {s:.0f}"
        ).format(c=m["centre"], ce=m["centre_err"], f=m["fwhm"], ew=m["ew"], ee=m["ew_err"], ef=m["ew_fit"], s=m["snr"])
        lo, hi = sorted((self.lo.value(), self.hi.value()))
        inside = (self.wave >= lo) & (self.wave <= hi)
        ww, ff = self.wave[inside], self.flux[inside]
        edges = np.interp(ww, [ww[0], ww[-1]], [np.median(ff[:3]), np.median(ff[-3:])])
        deepest = ww[np.argmax(np.abs(ff - edges))]  # where the data depart most from the edges' continuum
        step = float(np.median(np.diff(ww)))
        if not lo + m["fwhm"] < m["centre"] < hi - m["fwhm"] or abs(deepest - m["centre"]) > max(
            m["fwhm"] / 2, 2 * step
        ):
            # the continuum is read at the window's edges: a window inside the line gives a fit off the line
            text += " " + self.tr("The line reaches the edge of the window: widen it so both sides show continuum.")
        self.status.setText(text)
        self._plot()
        return m

    def _vr(self):
        from ..spectroscopy.analysis import v_over_r

        if not self._ready():
            return None
        try:
            v = v_over_r(self.wave, self.flux, self.vr_centre.value(), self.vr_half.value())
        except ValueError as e:
            self.status.setText(translate(e))
            return None
        self.status.setText(
            self.tr("V/R = {vr:.3f}; peaks at {vv:.0f} and {rv:.0f} km/s").format(
                vr=v["v_over_r"], vv=v["v_velocity"], rv=v["r_velocity"]
            )
        )
        return v

    def measure_series(self, paths):
        """Measure the current window (and V/R if both peaks are in emission) in each file."""
        from ..spectroscopy.analysis import measure_line, v_over_r
        from ..spectroscopy.rv import continuum_normalise

        rows = []
        for path in paths:
            got = self._read(path)
            if got is None:
                continue
            w, f, _, h = got
            try:
                m = measure_line(w, f, self.lo.value(), self.hi.value(), self.profile.currentData())
            except (ValueError, RuntimeError):
                continue
            try:
                m["v_over_r"] = v_over_r(w, continuum_normalise(w, f), self.vr_centre.value(), self.vr_half.value())[
                    "v_over_r"
                ]
            except ValueError:
                pass
            date = str(h.get("DATE-OBS", "")) if h is not None else ""
            self._add_row(f"{Path(path).name} {date}".strip(), m)
            rows.append((date, m))
        self.status.setText(self.tr("{n} spectra measured.").format(n=len(rows)))
        return rows

    def _series(self):
        paths, _ = QFileDialog.getOpenFileNames(self, self.tr("Spectra"), "", SPECTRA)
        if paths:
            self.measure_series(paths)

    # --- changes -------------------------------------------------------------
    def _smooth(self):
        from ..spectroscopy.analysis import smooth

        if self._ready():
            self._change(
                smooth(self.flux, self.smooth_kind.currentData(), self.smooth_width.value()), self.tr("Smoothed.")
            )

    def _arith(self):
        from ..spectroscopy.analysis import arithmetic

        if not self._ready():
            return
        op = {"+": "+", "−": "-", "×": "*", "÷": "/"}[self.op.currentText()]
        text = self.constant.text().strip().replace(",", ".")
        if text:
            try:
                other = (None, float(text))
            except ValueError:
                self.status.setText(self.tr("Not a number: {text}").format(text=text))
                return
        elif self.b is None:
            self.status.setText(self.tr("Open spectrum B first, or type a number."))
            return
        else:
            other = self.b
        self._change(arithmetic(self.wave, self.flux, *other, op), self.tr("Done."), self.tr("arithmetic"))

    def _resample(self):
        from ..spectroscopy.analysis import resample

        if self._ready():
            self.edit(self.tr("resample"), self._set_grid, *resample(self.wave, self.flux, self.step.value()))

    def _set_grid(self, wave, flux):
        self.history.append(self.flux)
        self.wave, self.flux = wave, flux
        self.status.setText(self.tr("Resampled."))
        self.last = None
        self._plot()

    def _normalise(self):
        from ..spectroscopy.rv import continuum_normalise

        if self._ready():
            self._change(continuum_normalise(self.wave, self.flux), self.tr("Normalised."))

    def _normalise_points(self):
        from ..spectroscopy.analysis import continuum_from_points

        if not self._ready():
            return
        try:
            cont = continuum_from_points(self.wave, self.flux, self.points)
        except ValueError as e:
            self.status.setText(translate(e))
            return
        self.pick.setChecked(False)
        self.edit(self.tr("normalise through points"), self._through_points, cont)

    def _through_points(self, cont):
        self.points = []
        self._change(self.flux / cont, self.tr("Normalised."))

    def compute_response(self, reference_path):
        from ..spectroscopy.analysis import response

        got = self._read(reference_path)
        if got is None or not self._ready():
            return None
        try:
            self.resp = (self.wave.copy(), response(self.wave, self.flux, got[0], got[1]))
        except ValueError as e:
            self.status.setText(translate(e))
            return None
        self.apply_resp.setEnabled(True)
        self.status.setText(self.tr("Response computed; open a target spectrum and press Divide by response."))
        return self.resp

    def _response(self):
        path = QFileDialog.getOpenFileName(self, self.tr("Reference flux distribution"), "", SPECTRA)[0]
        if path:
            self.compute_response(path)

    def _apply_response(self):
        from ..spectroscopy.analysis import resample_onto

        if self._ready() and self.resp is not None:
            self._change(self.flux / resample_onto(self.wave, *self.resp), self.tr("Relative flux (response removed)."))

    def _undo(self):
        self.undo_stack.undo()

    def _save(self, path=None):
        from ..spectroscopy import spectrum_io

        if not self._ready():
            return None
        path = path or QFileDialog.getSaveFileName(self, self.tr("Save spectrum"), "spectrum.fits", "FITS (*.fits)")[0]
        if path:
            spectrum_io.write(path, self.wave, self.flux, np.full(self.flux.size, np.nan), self.header)
            self.status.setText(self.tr("Saved: {path}").format(path=path))
        return path

    def _bess(self, path=None, meta=None):
        from ..spectroscopy.analysis import write_bess

        if not self._ready():
            return None
        if meta is None:
            d = BessDialog(self.header, self)
            if d.exec() != QDialog.Accepted:
                return None
            meta = d.values()
        path = path or QFileDialog.getSaveFileName(self, self.tr("BeSS file"), "bess.fits", "FITS (*.fits)")[0]
        if path:
            write_bess(path, self.wave, self.flux, meta)
            self.status.setText(self.tr("Saved: {path}").format(path=path))
        return path


class BessDialog(QDialog):
    """The BeSS keywords the spectrum's header does not already give."""

    FIELDS = ("object", "observer", "date_obs", "exptime", "instrument", "site", "latitude", "longitude", "elevation")
    KEYS = ("OBJECT", "OBSERVER", "DATE-OBS", "EXPTIME", "INSTRUME", "SITENAME", "SITELAT", "SITELONG", "SITEELEV")

    def __init__(self, header=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Export for BeSS / ARAS"))
        form = QFormLayout(self)
        labels = (
            self.tr("Object (Simbad name)"),
            self.tr("Observer"),
            self.tr("Start of exposure (UTC)"),
            self.tr("Exposure (s)"),
            self.tr("Telescope + spectrograph + camera"),
            self.tr("Site"),
            self.tr("Latitude (°)"),
            self.tr("Longitude (°)"),
            self.tr("Elevation (m)"),
        )
        self.edits = {}
        for field, key, label in zip(self.FIELDS, self.KEYS, labels, strict=True):
            e = QLineEdit(str((header or {}).get(key, "")), self)
            self.edits[field] = e
            e.setToolTip(self.tr("A keyword BeSS requires; filled from the spectrum's header when it has it"))
            form.addRow(label, e)
        self.telluric = QCheckBox(self.tr("Telluric lines removed"), self)
        self.cosmic = QCheckBox(self.tr("Cosmic rays removed"), self)
        self.cosmic.setToolTip(self.tr("Tick if cosmic-ray hits were removed; written into the header for BeSS"))
        self.telluric.setToolTip(
            self.tr("Tick if the telluric (atmospheric) lines were divided out; written into the header for BeSS")
        )
        self.vhel = QLineEdit("0", self)
        self.vhel.setToolTip(
            self.tr(
                "The heliocentric velocity correction already applied to the wavelengths (0 if none); BeSS "
                "needs it to compare spectra"
            )
        )
        form.addRow(self.telluric)
        form.addRow(self.cosmic)
        form.addRow(self.tr("Heliocentric correction applied (km/s)"), self.vhel)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self):
        out = {k: e.text().strip() for k, e in self.edits.items()}
        for k in ("exptime", "latitude", "longitude", "elevation"):
            try:
                out[k] = float(out[k].replace(",", "."))
            except ValueError:
                out[k] = 0.0
        try:
            out["vhel"] = float(self.vhel.text().replace(",", "."))
        except ValueError:
            out["vhel"] = 0.0
        return out | {"telluric": self.telluric.isChecked(), "cosmic": self.cosmic.isChecked()}

"""The Period search page: light curve, cleaning, periodograms and the folded curve."""

from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .kit.widgets import PlotCanvas, StepGuide
from .messages import translate
from .undo import Undoable


class PeriodPage(Undoable, QWidget):
    """Period search on a light curve (from the Photometry window or a CSV file) and phase folding."""

    search_requested = Signal(list, list, dict)  # time, flux, params
    archive_requested = Signal(str, str)  # target, mission

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_undo()
        self.time, self.flux, self.best, self.periodogram = None, None, None, None
        self.err = None  # the points' errors when the light curve has them (error bars, weights of the search)
        split = QSplitter(Qt.Horizontal, self)
        left = QWidget(self)
        lay = QVBoxLayout(left)
        self.guide = StepGuide(
            [
                (
                    self.tr("Get a light curve: from the Photometry window, a CSV file or an archive"),
                    self.tr(
                        "Load a CSV file, or type the star's name, choose the archive (TESS, Kepler, K2, ZTF, AAVSO) "
                        "and press Download. A light curve measured in the Photometry window arrives here by itself."
                    ),
                ),
                (
                    self.tr("Clean it if needed: outliers, bad points, binning"),
                    self.tr(
                        "Remove outliers (σ) or Delete points by clicking; Bin in time for dense data. Skip this "
                        "when the curve looks clean."
                    ),
                ),
                (
                    self.tr("Search for the period"),
                    self.tr(
                        "Choose the method (Lomb–Scargle for pulsating stars, BLS for transits and Algol-type "
                        "eclipses, PDM or ANOVA for any shape) and the period range, then press Search."
                    ),
                ),
                (
                    self.tr("Check the periodogram and the folded light curve"),
                    self.tr(
                        "A right period gives a clean fold. For an eclipsing binary the true period is often twice "
                        "the strongest Lomb–Scargle peak; check the aliases too. Then go on to Frequency analysis or "
                        "the O-C diagram."
                    ),
                ),
            ],
            self,
        )
        lay.addWidget(self.guide)
        self.source = QLabel(
            self.tr("No light curve yet: measure one in the Photometry window or load a CSV file."), self
        )
        self.source.setWordWrap(True)
        lay.addWidget(self.source)
        load = self.load_button = QPushButton(self.tr("Load CSV (time, flux; or AAVSO / ZTF / ASAS-SN files)…"), self)
        load.setToolTip(
            self.tr(
                "Any table with a time column and a brightness column; files downloaded from AAVSO, ZTF and"
                " ASAS-SN are recognised"
            )
        )
        load.clicked.connect(self._load)
        save = self.save_button = QPushButton(self.tr("Save light curve (CSV)…"), self)
        save.setToolTip(
            self.tr(
                "The light curve as shown (downloaded, edited) in a CSV file: open it in the Models window "
                "or in another program"
            )
        )
        save.clicked.connect(self._save)
        lay.addWidget(load)  # one under the other: side by side they kept the column wider than a small window
        lay.addWidget(save)
        row = QHBoxLayout()
        self.archive_target = QLineEdit(self)
        self.archive_target.setPlaceholderText(self.tr("star name, e.g. AI Dra or TIC 12345678"))
        self.archive_target.setToolTip(
            self.tr("The star's name or catalogue number as the archive knows it; Enter starts the download")
        )
        self.mission = QComboBox(self)
        self.mission.addItems(("TESS", "Kepler", "K2", "ZTF", "AAVSO"))
        self.mission.setToolTip(self.tr("The archive to download the light curve from"))
        fetch = self.fetch_button = QPushButton(self.tr("Download"), self)
        fetch.setToolTip(
            self.tr("TESS / Kepler / K2 from MAST, ZTF from IRSA, AAVSO observations (needs the internet)")
        )
        fetch.clicked.connect(self._fetch)
        self.archive_target.returnPressed.connect(self._fetch)
        for w in (self.archive_target, self.mission, fetch):
            row.addWidget(w)
        lay.addLayout(row)
        grid = QGridLayout()
        self.method = QComboBox(self)
        self.method.addItem(self.tr("Lomb–Scargle (pulsating stars)"), "lomb-scargle")
        self.method.addItem(self.tr("BLS (transits, Algol-type eclipses)"), "bls")
        self.method.addItem(self.tr("PDM (any shape)"), "pdm")
        self.method.addItem(self.tr("ANOVA (multi-harmonic, any smooth shape)"), "anova")
        for i, about in enumerate(
            (
                self.tr("Fits a sine wave at every trial period; the power is the share of the variance the sine "
                        "explains (Lomb 1976, Scargle 1982)."),
                self.tr("Fits a box-shaped dip (depth, duration, phase) at every trial period (Kovács, Zucker & "
                        "Mazeh 2002)."),
                self.tr("Folds the data on every trial period and compares the scatter inside phase bins with the "
                        "total scatter (Stellingwerf 1978)."),
                self.tr("Fits a Fourier series of two harmonics at every trial period; the F statistic of that fit "
                        "(Schwarzenberg-Czerny 1996)."),
            )
        ):  # fmt: skip
            self.method.setItemData(i, about, Qt.ToolTipRole)
        self.method.setToolTip(
            self.tr(
                "Lomb–Scargle: sine-like curves (pulsations, spots); BLS: short, box-shaped dips; PDM and "
                "ANOVA: curves of any shape, e.g. eclipsing binaries with two minima. The formulas: Guide, "
                "Mathematics of the methods"
            )
        )
        self.p_min, self.p_max = QDoubleSpinBox(self), QDoubleSpinBox(self)
        for w, v in ((self.p_min, 0.05), (self.p_max, 10.0)):
            w.setDecimals(4)
            w.setRange(0.001, 10000)
            w.setValue(v)
        grid.addWidget(QLabel(self.tr("Method"), self), 0, 0)
        grid.addWidget(self.method, 0, 1)
        grid.addWidget(QLabel(self.tr("Shortest period (d)"), self), 1, 0)
        grid.addWidget(self.p_min, 1, 1)
        self.p_min.setToolTip(
            self.tr("Shortest period searched; shorter than twice the time between points cannot be found")
        )
        grid.addWidget(QLabel(self.tr("Longest period (d)"), self), 2, 0)
        grid.addWidget(self.p_max, 2, 1)
        self.p_max.setToolTip(self.tr("Longest period searched; the data should cover at least two cycles of it"))
        from PySide6.QtWidgets import QSpinBox

        self.phase_bins = QSpinBox(self)
        self.phase_bins.setRange(0, 1000)
        self.phase_bins.setValue(0)
        self.phase_bins.setSpecialValueText(self.tr("off"))
        self.phase_bins.setToolTip(self.tr("Mean curve in this many phase bins on the folded plot"))
        self.phase_bins.valueChanged.connect(lambda _: self.best and self._plot_phase())
        grid.addWidget(QLabel(self.tr("Phase bins"), self), 3, 0)
        grid.addWidget(self.phase_bins, 3, 1)
        lay.addLayout(grid)
        edit = QGridLayout()
        self.clip_sigma = QDoubleSpinBox(self)
        self.clip_sigma.setRange(1.0, 20.0)
        self.clip_sigma.setValue(4.0)
        self.clip_sigma.setToolTip(self.tr("Limit in standard deviations for Remove outliers"))
        clip = self.clip_button = QPushButton(self.tr("Remove outliers (σ)"), self)
        clip.clicked.connect(lambda: self.edit(self.tr("remove outliers"), self._clip))
        clip.setToolTip(
            self.tr(
                "Removes points further than this many standard deviations from the median of their "
                "neighbours in time (cosmic rays, bad frames); Ctrl+Z brings them back"
            )
        )
        self.bin_minutes = QDoubleSpinBox(self)
        self.bin_minutes.setRange(0.1, 10000)
        self.bin_minutes.setValue(5.0)
        self.bin_minutes.setToolTip(self.tr("Length of a time bin in minutes for Bin in time"))
        binb = self.bin_button = QPushButton(self.tr("Bin in time (min)"), self)
        binb.clicked.connect(lambda: self.edit(self.tr("bin in time"), self._bin))
        binb.setToolTip(
            self.tr(
                "Averages the points in time bins of this length: less noise, fewer points; keep the bins "
                "much shorter than an eclipse"
            )
        )
        self.delete_mode = QPushButton(self.tr("Delete points by clicking"), self)
        self.delete_mode.setCheckable(True)
        self.delete_mode.setToolTip(self.tr("Click a point on the light-curve plot to remove it"))
        units = self.units_button = QPushButton(self.tr("Flux ↔ magnitude"), self)
        units.clicked.connect(lambda: self.edit(self.tr("flux / magnitude"), self._convert))
        units.setToolTip(self.tr("Converts relative flux to magnitudes (−2.5 log) or back"))
        undo = self.undo_button = QPushButton(self.tr("Undo edits"), self)
        undo.clicked.connect(lambda: self.edit(self.tr("undo edits"), self._undo))
        undo.setToolTip(self.tr("Back to the light curve as it was loaded (Ctrl+Z takes back one step at a time)"))
        edit.addWidget(clip, 0, 0)
        edit.addWidget(self.clip_sigma, 0, 1)
        edit.addWidget(binb, 1, 0)
        edit.addWidget(self.bin_minutes, 1, 1)
        edit.addWidget(self.delete_mode, 2, 0)
        edit.addWidget(units, 2, 1)
        edit.addWidget(undo, 3, 0)
        lay.addLayout(edit)
        self.search_button = QPushButton(self.tr("Search"), self)
        self.search_button.setEnabled(False)
        self.search_button.clicked.connect(self._search)
        self.search_button.setToolTip(
            self.tr(
                "Computes the periodogram between the shortest and longest period and folds the curve on "
                "the best period; check the folded plot by eye"
            )
        )
        lay.addWidget(self.search_button)
        self.result = QLabel(self)
        self.result.setWordWrap(True)
        self.result.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.result)
        lay.addStretch(1)
        split.addWidget(left)
        self.plot = PlotCanvas(self)
        self.plot.canvas.mpl_connect("button_press_event", self._clicked)
        split.addWidget(self.plot)
        split.setSizes([380, 800])
        QVBoxLayout(self).addWidget(split)
        self.original, self.magnitudes = None, False

    def _fetch(self):
        if self.archive_target.text().strip():
            source = {"ZTF": "IRSA", "AAVSO": "AAVSO"}.get(self.mission.currentText(), "MAST")
            self.source.setText(self.tr("Downloading from {source}…").format(source=source))
            self.archive_requested.emit(self.archive_target.text().strip(), self.mission.currentText())

    def undo_state(self):
        return {
            "time": self.time,
            "flux": self.flux,
            "err": self.err,
            "mag": self.magnitudes,
            "source": self.source.text(),
        }

    def set_undo_state(self, st):
        self.time, self.flux, self.magnitudes = st["time"], st["flux"], st["mag"]
        self.err = st.get("err")
        self.source.setText(st["source"])
        self.search_button.setEnabled(bool(self.time) and len(self.time) > 10)
        self._plot_light_curve()

    def set_light_curve(self, time, flux, label, keep_original=False, err=None):
        """err: the points' errors (same units as flux), drawn as error bars and used as weights by Lomb–Scargle and
        BLS; None when the source has none."""
        self.time, self.flux = list(time), list(flux)
        ok = err is not None and len(err) == len(self.time) and np.all(np.isfinite(np.asarray(err, float)))
        self.err = [float(e) for e in err] if ok and np.all(np.asarray(err, float) > 0) else None
        if not keep_original:
            self.undo_stack.clear()  # another star: the edits of the last one do not apply
            self.original, self.magnitudes, self.label = (self.time, self.flux, self.err), False, label
            self.best = None  # a new star: the old period does not apply
            self.guide.reset()
        self.guide.set_state(0, "done")
        if keep_original:
            self.guide.set_state(1, "done")
        self.source.setText(self.tr("{n} points from {source}").format(n=len(self.time), source=label))
        self.search_button.setEnabled(len(self.time) > 10)
        self._plot_light_curve()

    def _edited(self, t, y, what, err=None):
        e = None if err is None else np.asarray(err).tolist()
        self.set_light_curve(np.asarray(t).tolist(), np.asarray(y).tolist(), f"{self.label}, {what}", True, e)

    def _errs(self, idx=None):
        """The errors (of the points idx), or None."""
        if self.err is None:
            return None
        e = np.asarray(self.err, float)
        return e if idx is None else e[idx]

    def _clip(self):
        if self.time:
            keep = fourier_edit().sigma_clip(self.flux, self.clip_sigma.value(), self.time, self.best)
            t, y = np.asarray(self.time)[keep], np.asarray(self.flux)[keep]
            self._edited(t, y, self.tr("outliers removed"), self._errs(keep))

    def _bin(self):
        if self.time:
            binned = fourier_edit().bin_time(self.time, self.flux, self.bin_minutes.value() / 1440, self._errs())
            self._edited(*binned[:2], self.tr("binned"), binned[2] if len(binned) > 2 else None)

    def _convert(self):
        if self.time:
            from ..core.units import flux_to_mag, mag_to_flux

            y = np.asarray(self.flux, float)
            if not self.magnitudes and np.any(y <= 0):
                self.source.setText(self.tr("Fluxes must be positive to convert to magnitudes."))
                return
            e = self._errs()
            self.magnitudes = not self.magnitudes
            convert = flux_to_mag if self.magnitudes else mag_to_flux  # σm = 1.0857 σF / F, and back
            y, e = convert(y, e) if e is not None else (convert(y), None)
            self._edited(self.time, y, self.tr("magnitudes") if self.magnitudes else self.tr("flux"), e)

    def _undo(self):
        if self.original:
            self.magnitudes = False
            t, y, e = self.original
            self.set_light_curve(t, y, self.label, True, e)

    def _clicked(self, event):
        if not (self.delete_mode.isChecked() and self.time and event.inaxes is not None and event.xdata is not None):
            return
        ax = event.inaxes
        t, y = np.asarray(self.time), np.asarray(self.flux)
        x = t - ax._t_ref if getattr(ax, "_kind", "") == "time" else fold_phase(t, self.best, self._t0())
        if getattr(ax, "_kind", "") not in ("time", "phase"):
            return
        (x0, x1), (y0, y1) = ax.get_xlim(), ax.get_ylim()
        d = np.hypot((x - event.xdata) / (x1 - x0), (y - event.ydata) / (y1 - y0))
        i = int(np.argmin(d))
        if d[i] < 0.02:
            e = None if self.err is None else np.delete(np.asarray(self.err), i)
            self.edit(
                self.tr("delete a point"), self._edited, np.delete(t, i), np.delete(y, i), self.tr("points deleted"), e
            )

    def _t0(self):
        t, f = np.asarray(self.time), np.asarray(self.flux)
        return t[np.argmax(f) if self.magnitudes else np.argmin(f)]

    def _plot_light_curve(self):
        if self.best:
            return self._plot_phase()
        self.plot.figure.clear()
        ax = self.plot.figure.subplots()
        ax._kind = "time"
        t = np.asarray(self.time)
        ax._t_ref = float(np.floor(t.min())) if t.size and t.min() > 1000 else 0.0  # JD: "+2.46e6" says nothing
        if self.err is not None:
            ax.errorbar(t - ax._t_ref, self.flux, self.err, fmt=".", ms=2, lw=0.5, elinewidth=0.5, alpha=0.8)
        else:
            ax.plot(t - ax._t_ref, self.flux, ".", ms=2)
        ax.set_xlabel(self.tr("Time − {t:.0f} (d)").format(t=ax._t_ref) if ax._t_ref else self.tr("Time (d)"))
        ax.set_ylabel(self.tr("Magnitude") if self.magnitudes else self.tr("Relative flux"))
        if self.magnitudes:
            ax.invert_yaxis()
        self.plot.draw()

    def _load(self, path=None):
        """path: a file opened from the window's File menu or dropped on it; otherwise (a button click) asked."""
        if not isinstance(path, str):
            path, _ = QFileDialog.getOpenFileName(
                self, self.tr("Load light curve"), "", "CSV (*.csv *.txt *.dat);;Light-curve file (*.lc.ecsv *.ecsv)"
            )
        if not path:
            return
        from ..photometry import lcfile
        from ..timeseries import surveys

        if lcfile.is_lcfile(path):
            try:
                t, flux, err, _ = lcfile.series(path)
            except (OSError, ValueError, KeyError) as e:
                self.source.setText(
                    self.tr("Cannot read {file}: {error}").format(file=Path(path).name, error=translate(e))
                )
                return
            return self.set_light_curve(t, flux, Path(path).name, err=err)

        try:
            rows = surveys.parse(Path(path).read_text(encoding="utf-8", errors="replace"))
        except (OSError, ValueError, UnicodeError):
            rows = []
        if len(rows) >= 3:  # a survey or database export: one band, magnitudes as relative flux
            try:
                lc = surveys.to_light_curve(rows)
                return self.set_light_curve(
                    lc["time"], lc["rel_flux"], f"{Path(path).name} ({lc['band']})", err=lc.get("rel_flux_err")
                )
            except ValueError:
                pass  # not enough points in one band: read it as a plain table
        try:
            data = np.genfromtxt(
                path,
                delimiter="," if path.endswith(".csv") else None,
                names=None,
                skip_header=1 if not Path(path).read_text().lstrip()[:1].isdigit() else 0,
            )
            err = data[:, 2] if data.ndim == 2 and data.shape[1] >= 3 else None  # a third column: the errors
            self.set_light_curve(data[:, 0], data[:, 1], Path(path).name, err=err)
        except (ValueError, IndexError) as e:
            self.source.setText(self.tr("Cannot read {file}: {error}").format(file=Path(path).name, error=translate(e)))

    def save_csv(self, path):
        """Time and flux (or magnitude) columns that the Orbits & models page reads back."""
        column = "mag" if self.magnitudes else "rel_flux"
        if self.err is not None:
            rows = "\n".join(f"{t:.7f},{y:.7g},{e:.3g}" for t, y, e in zip(self.time, self.flux, self.err, strict=True))
            Path(path).write_text(f"time,{column},{column}_err\n{rows}\n", encoding="utf-8")
            return
        rows = "\n".join(f"{t:.7f},{y:.7g}" for t, y in zip(self.time, self.flux, strict=True))
        Path(path).write_text(f"time,{column}\n{rows}\n", encoding="utf-8")

    def _save(self):
        if not self.time:
            self.source.setText(self.tr("No light curve to save yet."))
            return
        name = "".join(c if c.isalnum() or c in "-_" else "_" for c in self.label.split(" (")[0])[:60]
        path, _ = QFileDialog.getSaveFileName(self, self.tr("Save light curve"), f"{name}.csv", "CSV (*.csv)")
        if path:
            self.save_csv(path)
            self.source.setText(self.tr("Saved {n} points to {file}").format(n=len(self.time), file=Path(path).name))

    def _search(self):
        self.result.setText(self.tr("Searching…"))
        params = {"method": self.method.currentData(), "p_min": self.p_min.value(), "p_max": self.p_max.value()}
        if self.err is not None:
            params["err"] = self.err  # an input of the step (main window), not a parameter
        self.search_requested.emit(self.time, self.flux, params)

    def show_result(self, out):
        self.best, self.periodogram = out["best"], out
        if self.guide.states[1] is None:
            self.guide.set_state(1, "skipped")
        self.guide.set_state(2, "done")
        text = self.tr("Best period: {p:.6f} d").format(p=self.best)
        t = np.sort(self.time)
        cuts = np.flatnonzero(np.diff(t) > 20 * self.best) + 1  # stretches (seasons, sectors) apart
        if len(cuts):  # the cycle count across the widest gap is not certain: centre to centre of its sides
            i = int(np.argmax(t[cuts] - t[cuts - 1]))
            before = t[(cuts[i - 1] if i else 0) : cuts[i]]
            after = t[cuts[i] : (cuts[i + 1] if i + 1 < len(cuts) else len(t))]
            gap = float(np.mean(after) - np.mean(before))
            f, df = 1 / self.best, 1 / gap
            text += "\n" + self.tr(
                "The data come in stretches {g:.0f} d apart: one cycle more or less across the gap ({p1:.6f} or "
                "{p2:.6f} d) fits almost as well. Check with the times of minimum (O−C)."
            ).format(g=gap, p1=1 / (f + df), p2=1 / (f - df) if f > df else float("inf"))
        for warning in out.get("warnings") or []:  # the data may not hold this period (R5)
            warning = translate(warning)
            text += "\n⚠ " + warning[:1].upper() + warning[1:]
        self.result.setText(text)
        self._plot_phase()

    def _plot_phase(self):
        out = self.periodogram
        self.plot.figure.clear()
        ax, ax2 = self.plot.figure.subplots(2, 1)
        ax.plot(out["periods"], out["power"], lw=0.7)
        ax.axvline(self.best, color="r", lw=0.8)
        ax.set_xscale("log")
        ax.set_xlabel(self.tr("Period (d)"))
        ax.set_ylabel(self.tr("Power"))
        t, f = np.asarray(self.time), np.asarray(self.flux)
        ph = fold_phase(t, self.best, self._t0())
        ax2._kind = "phase"
        alpha = 0.5 if self.phase_bins.value() else 1
        if self.err is not None:
            ax2.errorbar(ph, f, self.err, fmt=".", ms=2, lw=0.5, elinewidth=0.5, alpha=alpha)
        else:
            ax2.plot(ph, f, ".", ms=2, alpha=alpha)
        if self.phase_bins.value():
            c, mean, err, _ = fourier_edit().bin_phase(ph, f, self.phase_bins.value())
            ax2.errorbar(c, mean, err, fmt="o", ms=3, color="C3", lw=0.8)
        ax2.set_xlabel(self.tr("Phase"))
        ax2.set_ylabel(self.tr("Magnitude") if self.magnitudes else self.tr("Relative flux"))
        if self.magnitudes:
            ax2.invert_yaxis()
        self.plot.draw()


def fold_phase(t, period, t0):
    from ..timeseries.period import fold

    return fold(t, period, t0)


def fourier_edit():
    from ..timeseries import fourier

    return fourier

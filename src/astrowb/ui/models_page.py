"""Orbits & models: fit a detached eclipsing binary or a transit, absolute dimensions with the SB2
orbit from Spectroscopy, export to PHOEBE and compare with a model curve computed there."""

from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..models.fit import DEFAULT_FREE, NAMES
from .kit.help import help_line
from .kit.widgets import PlotCanvas
from .messages import translate
from .spectro_page import _FileRow
from .undo import Undoable, track_typing

START = {
    "period": 1.0,
    "t0": 0.0,
    "r_sum": 0.2,
    "k": 0.8,
    "incl": 88.0,
    "j": 0.8,
    "ecosw": 0.0,
    "esinw": 0.0,
    "l3": 0.0,
}


class ModelsPage(Undoable, QWidget):
    fit_requested = Signal(dict, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_undo()
        self.setObjectName("orbits")
        self.result, self.orbit, self.overlay = None, None, None
        split = QSplitter(Qt.Horizontal, self)
        left = QWidget(self)
        lay = QVBoxLayout(left)
        from .kit.widgets import StepGuide

        self.guide = StepGuide(
            [
                (
                    self.tr("A light curve: measured here (Photometry) or downloaded (Light curves)"),
                    self.tr(
                        "Choose the light curve (CSV from the Photometry or Light curves window: Export CSV / Save "
                        "light curve)."
                    ),
                ),
                (
                    self.tr("Starting values: period and time of minimum (the ephemeris)"),
                    self.tr(
                        "Type the period and the time of a primary minimum (from the O−C window or the literature)."
                    ),
                ),
                (
                    self.tr("Fit, and look at the residuals and the warnings"),
                    self.tr(
                        "Press Fit. Look at the residuals under the curve and read the warnings: a star that fills "
                        "its Roche lobe (W UMa type) needs PHOEBE or Wilson–Devinney (the export buttons)."
                    ),
                ),
                (
                    self.tr("Errors and the table for the paper"),
                    self.tr("Posterior… shows the MCMC errors; Export results (CSV / LaTeX) writes the table."),
                ),
            ],
            self,
        )
        lay.addWidget(self.guide)
        self.file = _FileRow(self.tr("Light curve"), self, "Tables (*.csv *.txt *.dat);;All files (*)")
        lay.addWidget(self.file)
        self.file.edit.textChanged.connect(lambda t: self.guide.set_state(0, "done" if t.strip() else None))
        labels = {
            "period": self.tr("Period (d)"),
            "t0": self.tr("Primary minimum (BJD)"),
            "r_sum": self.tr("r1 + r2 (fraction of a)"),
            "k": self.tr("k = r2 / r1"),
            "incl": self.tr("Inclination (°)"),
            "j": self.tr("Surface brightness ratio J"),
            "ecosw": "e cos ω",
            "esinw": "e sin ω",
            "l3": self.tr("Third light"),
        }
        self.table = QTableWidget(len(NAMES), 3, self)
        self.table.setHorizontalHeaderLabels([self.tr("Parameter"), self.tr("Start / result"), self.tr("Fit")])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.checks = {}
        for r, name in enumerate(NAMES):
            item = QTableWidgetItem(labels[name])
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(r, 0, item)
            self.table.setItem(r, 1, QTableWidgetItem(f"{START[name]:g}"))
            box = QCheckBox(self.table)
            box.setChecked(name in DEFAULT_FREE)
            box.setToolTip(self.tr("Ticked: fitted; empty: kept at the value in the table"))
            self.table.setCellWidget(r, 2, box)
            self.checks[name] = box
        lay.addWidget(self.table, 1)
        grid = QGridLayout()
        self.ld = []
        for r, star in enumerate((self.tr("Star 1"), self.tr("Star 2"))):
            grid.addWidget(QLabel(self.tr("{star} limb darkening u1, u2").format(star=star), self), r, 0)
            pair = []
            for c, v in enumerate((0.4, 0.2)):
                s = QDoubleSpinBox(self)
                s.setRange(-1, 2)
                s.setDecimals(3)
                s.setSingleStep(0.05)
                s.setValue(v)
                s.valueChanged.connect(lambda _v: self.record(self.tr("limb darkening"), self._typed_from))
                s.setToolTip(
                    self.tr(
                        "Quadratic limb darkening, e.g. from Claret's tables for the star's temperature and the filter"
                    )
                )
                grid.addWidget(s, r, c + 1)
                pair.append(s)
            self.ld.append(pair)
        self._add_exposure(lay, grid)
        track_typing(self, self.table, self.tr("type a value"))
        for box in self.checks.values():
            box.toggled.connect(lambda _on: self.record(self.tr("free or fixed"), self._typed_from))
        self.use_orbit = QCheckBox(self.tr("Absolute dimensions with the double-lined orbit from Spectroscopy"), self)
        self.use_orbit.setEnabled(False)
        self.use_orbit.setToolTip(
            self.tr(
                "With the velocities' K1, K2 and the light curve's radii and inclination: masses and radii "
                "of both stars in solar units (needs a double-lined orbit fitted in the Spectroscopy window)"
            )
        )
        lay.addWidget(self.use_orbit)
        row = QHBoxLayout()
        self.use_mcmc = QCheckBox(self.tr("MCMC uncertainties (slower, for correlated parameters)"), self)
        self.use_mcmc.setToolTip(
            self.tr(
                "After the fit, a Markov chain explores the parameters: honest errors when they depend on "
                "each other (e.g. radii and inclination in partial eclipses). Slower."
            )
        )
        self.mcmc_steps = QSpinBox(self)
        self.mcmc_steps.setRange(200, 20000)
        self.mcmc_steps.setSingleStep(500)
        self.mcmc_steps.setValue(2000)
        self.mcmc_steps.setSuffix(self.tr(" steps"))
        self.mcmc_steps.setToolTip(self.tr("The most steps of the Markov chains; they stop earlier once converged"))
        row.addWidget(self.use_mcmc, 1)
        row.addWidget(self.mcmc_steps)
        lay.addLayout(row)
        row = QHBoxLayout()
        self.fit_button = QPushButton(self.tr("Fit"), self)
        self.fit_button.clicked.connect(lambda: self._run(None))
        self.fit_button.setToolTip(
            self.tr(
                "Fits two limb-darkened spheres on a Keplerian orbit (as EBOP / JKTEBOP) to the light "
                "curve; the ticked parameters are free, the others fixed at their values"
            )
        )
        export = self.phoebe_button = QPushButton(self.tr("Fit and export for PHOEBE…"), self)
        export.clicked.connect(self._export)
        export.setToolTip(
            self.tr(
                "Fits, then writes the light curve and the fitted values as starting values for a full model in PHOEBE"
            )
        )
        wd = self.wd_button = QPushButton(self.tr("Fit and export for WD…"), self)
        wd.setToolTip(self.tr("Observations in WD's columns and the starting values under WD's names"))
        wd.clicked.connect(lambda: self._export("wd"))
        transit = self.transit_button = QPushButton(self.tr("Fit and export for ExoClock / ETD…"), self)
        transit.setToolTip(
            self.tr("Upload files for the ExoClock and Exoplanet Transit Database projects, and the transit's mid-time")
        )
        transit.clicked.connect(lambda: self._export("transit"))
        overlay = self.overlay_button = QPushButton(self.tr("Compare with a model curve…"), self)
        overlay.setToolTip(self.tr("Two columns: phase (or time) and flux, e.g. computed in PHOEBE"))
        overlay.clicked.connect(self._load_overlay)
        self.posterior_button = QPushButton(self.tr("Posterior…"), self)
        self.posterior_button.clicked.connect(self.show_posterior)
        self.posterior_button.setToolTip(
            self.tr(
                "The MCMC samples: each parameter's distribution and how the parameters depend on each "
                "other (corner plot)"
            )
        )
        self.posterior_button.hide()
        from .plot.export import results_button

        results = self.results_button = results_button(self, self.fit_table)
        buttons = QGridLayout()  # two per row: the page fits narrow windows in every language
        for i, b in enumerate((self.fit_button, export, wd, transit, overlay, results, self.posterior_button)):
            buttons.addWidget(b, i // 2, i % 2)
        lay.addLayout(buttons)
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.status)
        lay.addWidget(help_line(self.tr("Two spheres on a Keplerian orbit: detached binaries and transits. Contact "
                                        "binaries: PHOEBE or WD."), "orbits-models-model", self))  # fmt: skip
        split.addWidget(left)
        self.plot = PlotCanvas(self)
        split.addWidget(self.plot)
        split.setSizes([430, 770])
        from .visual_orbit_tab import VisualOrbitTab

        self.tabs = QTabWidget(self)
        self.tabs.addTab(split, self.tr("Eclipsing binary / transit"))
        self.visual_tab = VisualOrbitTab(self)
        self.tabs.addTab(self.visual_tab, self.tr("Visual binary orbit"))
        QVBoxLayout(self).addWidget(self.tabs)

    def _add_exposure(self, lay, grid):
        """The exposure time the model is averaged over (models.fit.model), under the limb darkening; then the grid."""
        grid.addWidget(QLabel(self.tr("Exposure time"), self), 2, 0)
        self.exposure = QDoubleSpinBox(self)
        self.exposure.setRange(0, 7200)
        self.exposure.setDecimals(1)
        self.exposure.setSuffix(self.tr(" s"))
        self.exposure.setSpecialValueText(self.tr("short (none)"))
        self.exposure.setToolTip(
            self.tr(
                "Long exposures smear the eclipses: the model is averaged over each one (TESS full frames 1800 s "
                "or 600 s, Kepler long cadence 1765 s). Leave at none for exposures of a few minutes or less."
            )
        )
        grid.addWidget(self.exposure, 2, 1)
        lay.addLayout(grid)

    def set_orbit(self, orbit):
        """The latest orbit fitted in the Spectroscopy window; only double-lined orbits give dimensions."""
        self.orbit = orbit if orbit and "k2" in orbit else None
        self.use_orbit.setEnabled(self.orbit is not None)
        self.use_orbit.setChecked(self.orbit is not None)

    def _start(self):
        out = {}
        for r, name in enumerate(NAMES):
            try:
                out[name] = float(self.table.item(r, 1).text())
            except (AttributeError, ValueError):
                raise ValueError(
                    self.tr("Value of {p} not understood.").format(p=self.table.item(r, 0).text())
                ) from None
        return out

    def _run(self, export_dir):
        if not self.file.text():
            self.status.setText(self.tr("Choose a light-curve file."))
            return
        try:
            start = self._start()
        except ValueError as e:
            self.status.setText(translate(e))
            return
        if start["period"] <= 0:
            self.status.setText(self.tr("Give the period and the time of primary minimum (O-C tab)."))
            return
        inputs = {"light_curve": self.file.text(), "start": start}
        if self.use_orbit.isChecked() and self.orbit:
            inputs["orbit"] = self.orbit
        if export_dir:
            inputs["export_dir"] = export_dir
        params = {
            "free": [n for n in NAMES if self.checks[n].isChecked()],
            "ld1": [s.value() for s in self.ld[0]],
            "ld2": [s.value() for s in self.ld[1]],
            "mcmc_steps": self.mcmc_steps.value() if self.use_mcmc.isChecked() else 0,
            "export_format": getattr(self, "export_format", "phoebe"),
            "exposure": self.exposure.value(),
        }
        self.status.setText(self.tr("Fitting…"))
        self.fit_requested.emit(inputs, params)

    def _export(self, export_format="phoebe"):
        title = {
            "wd": self.tr("Folder for the WD files"),
            "transit": self.tr("Folder for the transit report"),
        }.get(export_format, self.tr("Folder for the PHOEBE files"))
        folder = QFileDialog.getExistingDirectory(self, title)
        if folder:
            self.export_format = export_format
            self._run(folder)

    def _load_overlay(self):
        path, _ = QFileDialog.getOpenFileName(self, "", "", "Tables (*.txt *.dat *.csv);;All files (*)")
        if path:
            self.load_overlay(path)

    def load_overlay(self, path):
        from ..models.data import read_model_curve

        try:
            x, f = read_model_curve(path)
        except Exception as e:  # not a table of phase (or time) and flux
            from PySide6.QtWidgets import QMessageBox

            from .messages import translate

            QMessageBox.warning(self, self.tr("Model curve"), f"{path}\n\n{translate(str(e))}")
            return None
        if self.result and np.nanmax(np.abs(x)) > 2:  # times: fold with the fitted ephemeris
            p = self.result["params"]
            x = ((x - p["t0"]) / p["period"] + 0.25) % 1 - 0.25
        self.overlay = (x, f / np.nanmedian(f[f >= np.nanpercentile(f, 50)]))  # >=: a flat out-of-eclipse part
        self._draw()

    # --- undo / redo of the parameters (Edit menu, Ctrl+Z / Ctrl+Y) -----------
    def undo_state(self):
        values = tuple(self.table.item(r, 1).text() for r in range(len(NAMES)))
        free = tuple(self.checks[n].isChecked() for n in NAMES)
        return values, free, tuple(s.value() for pair in self.ld for s in pair)

    def set_undo_state(self, state):
        values, free, ld = state
        widgets = [*self.checks.values(), *(s for pair in self.ld for s in pair)]
        for w in (self.table, *widgets):
            w.blockSignals(True)
        for r, text in enumerate(values):
            self.table.item(r, 1).setText(text)
        for n, on in zip(NAMES, free, strict=True):
            self.checks[n].setChecked(on)
        for s, v in zip((s for pair in self.ld for s in pair), ld, strict=True):
            s.setValue(v)
        for w in (self.table, *widgets):
            w.blockSignals(False)

    def _fill_values(self, params):
        for row, name in enumerate(NAMES):
            self.table.item(row, 1).setText(f"{params[name]:.8g}")

    def show_fit(self, r):
        self.result = r
        self.guide.set_state(1, "done")
        self.guide.set_state(2, "done")
        if r.get("mcmc"):
            self.guide.set_state(3, "done")
        self.edit(self.tr("fitted values"), self._fill_values, r["params"])
        p, e, d, de = r["params"], r["errors"], r["derived"], r["derived_err"]
        text = self.tr(
            "i = {i:.3f} ± {ie:.3f}°, r1 = {r1:.5f} ± {r1e:.5f}, r2 = {r2:.5f} ± {r2e:.5f}, "
            "L2/L1 = {lr:.4f} ± {lre:.4f}, e = {ecc:.4f} ± {ee:.4f}, rms = {rms:.5f}, χ²ᵣ = {chi:.2f} ({n} points)"
        ).format(
            i=p["incl"],
            ie=e["incl"],
            r1=d["r1"],
            r1e=de["r1"],
            r2=d["r2"],
            r2e=de["r2"],
            lr=d["light_ratio"],
            lre=de["light_ratio"],
            ecc=d["e"],
            ee=de["e"],
            rms=r["rms"],
            chi=r["chi2r"],
            n=r["n"],
        )
        roche = r.get("roche") or {}
        if roche.get("level") == "contact":
            text += "\n" + self.tr(
                "⚠ A star fills {f:.0f} % of its Roche lobe (lobe radius {l1:.3f} and {l2:.3f} for q = {q:.2f}): "
                "a semi-detached or contact (W UMa-type) binary. This model treats the stars as spheres and does "
                "not hold for it: the radii and the inclination are not reliable. Export the PHOEBE or "
                "Wilson–Devinney files and fit a Roche model there. Times of minimum and O−C are not affected."
            ).format(f=100 * roche["fill"], l1=roche["lobe1"], l2=roche["lobe2"], q=roche["q"])
        elif roche.get("level") == "distorted":
            text += "\n" + self.tr(
                "Note: a radius above 0.25 of the separation: the stars are tidally flattened by a few per cent and "
                "the spheres model is only approximate (its errors are too small). Check the result with PHOEBE."
            )
        a = r.get("absolute")
        if a:
            text += "\n" + self.tr(
                "M1 = {m1:.3f} ± {m1e:.3f} M☉, M2 = {m2:.3f} ± {m2e:.3f} M☉, R1 = {r1:.3f} ± {r1e:.3f} R☉, "
                "R2 = {r2:.3f} ± {r2e:.3f} R☉, a = {a:.3f} ± {ae:.3f} R☉, log g1 = {g1:.3f}, log g2 = {g2:.3f}"
            ).format(
                m1=a["m1"],
                m1e=a["m1_err"],
                m2=a["m2"],
                m2e=a["m2_err"],
                r1=a["r1"],
                r1e=a["r1_err"],
                r2=a["r2"],
                r2e=a["r2_err"],
                a=a["a"],
                ae=a["a_err"],
                g1=a["logg1"],
                g2=a["logg2"],
            )
        tr = r.get("transit")
        if tr:
            text += "\n" + self.tr(
                "Transit: Tc = {tc:.6f} ± {e:.6f} BJD_TDB (epoch {n}), depth {d:.5f}, T14 {h:.3f} h"
            ).format(tc=tr["tc"], e=tr["tc_err"], n=tr["epoch"], d=tr["depth"], h=tr["t14"] * 24)
        if r.get("exported"):
            text += "\n" + self.tr("Files written: {f}").format(f=str(Path(r["exported"][0]).parent))
        m = r.get("mcmc")
        if m:
            text += "\n" + self.tr("MCMC (acceptance {a:.2f}): ").format(a=m["acceptance"])
            text += ", ".join(  # a BJD needs its decimals: "2.4605e+06" says nothing
                f"{n} = {v[0]:{'.6f' if n == 't0' else '.6g'}} −{v[1]:.2g} +{v[2]:.2g}" for n, v in m["params"].items()
            )
        self.status.setText(text)
        self._draw()
        self.posterior_button.setVisible(bool(m))

    def fit_table(self):
        """(rows, caption) of the last light-curve fit for the results export."""
        r = self.result
        if not r:
            self.status.setText(self.tr("Fit the light curve first."))
            return None
        units = {"period": "d", "t0": "BJD_TDB", "incl": "deg"}
        m = (r.get("mcmc") or {}).get("params", {})
        rows = []
        for n in NAMES:
            if n in m:  # median and the larger of the two sides of the 68 % interval
                rows.append((n, m[n][0], max(m[n][1], m[n][2]), units.get(n, "")))
            elif n in r["free"]:
                rows.append((n, r["params"][n], r["errors"][n], units.get(n, "")))
            else:
                rows.append((n + " (fixed)", r["params"][n], None, units.get(n, "")))
        d, de = r["derived"], r["derived_err"]
        rows += [("r1", d["r1"], de["r1"], "a"), ("r2", d["r2"], de["r2"], "a"), ("e", d["e"], de["e"], "")]
        rows += [("omega", d["omega"], de["omega"], "deg"), ("L2/L1", d["light_ratio"], de["light_ratio"], "")]
        a = r.get("absolute") or {}
        for n, unit in (("m1", "Msun"), ("m2", "Msun"), ("r1", "Rsun"), ("r2", "Rsun"), ("a", "Rsun")):
            if n in a:
                rows.append((n.upper() if n != "a" else "a", a[n], a.get(n + "_err"), unit))
        for n in ("logg1", "logg2"):
            if n in a:
                rows.append((n, a[n], a.get(n + "_err"), "cgs"))
        t = r.get("transit")
        if t:
            rows += [
                ("Tc", t["tc"], t["tc_err"], "BJD_TDB"),
                ("depth", t["depth"], None, ""),
                ("T14", t["t14"] * 24, None, "h"),
            ]
        rows += [("rms", r["rms"], None, ""), ("chi2_r", r["chi2r"], None, "")]
        errors = (
            self.tr("medians and 68 % intervals of the MCMC posterior (the larger side)")
            if m
            else self.tr("1σ errors from the covariance matrix, derived quantities from its draws")
        )
        caption = self.tr(
            "Light-curve fit to {n} points: two limb-darkened spheres on a Keplerian orbit (EBOP / JKTEBOP "
            "approximation), least squares; {errors}."
        ).format(n=r["n"], errors=errors)
        return rows, caption

    def show_posterior(self):
        """Corner plot of the MCMC samples: histograms on the diagonal, pairs below."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout

        m = (self.result or {}).get("mcmc")
        if not m:  # reachable from the menu as well: say what to do instead of failing
            self.status.setText(self.tr("No posterior yet: tick MCMC uncertainties and press Fit."))
            return
        s = np.asarray(m["samples"])
        n = s.shape[1]
        dlg = QDialog(self)
        dlg.setWindowTitle(self.tr("Posterior"))
        dlg.resize(760, 720)
        canvas = PlotCanvas(dlg)
        QVBoxLayout(dlg).addWidget(canvas)
        axes = canvas.figure.subplots(n, n, squeeze=False)
        for i in range(n):
            for j in range(n):
                ax = axes[i][j]
                if j > i:
                    ax.set_visible(False)
                elif i == j:
                    ax.hist(s[:, i], bins=40, histtype="step")
                    for q in np.percentile(s[:, i], [16, 50, 84]):
                        ax.axvline(q, ls="--" if q != np.median(s[:, i]) else "-", lw=0.8)
                else:
                    ax.plot(s[:, j], s[:, i], ",", alpha=0.4)
                if i == n - 1:
                    ax.set_xlabel(m["names"][j], fontsize="small")
                if j == 0 and i > 0:
                    ax.set_ylabel(m["names"][i], fontsize="small")
                ax.tick_params(labelsize=6)
        canvas.draw()
        dlg.open()
        self.posterior_dialog = dlg
        return dlg

    def _draw(self):
        r = self.result
        self.plot.figure.clear()
        if not r:
            return
        ax, res = self.plot.figure.subplots(2, 1, sharex=True, gridspec_kw={"height_ratios": [3, 1]})
        ax.plot(r["phase"], r["flux"], ".", ms=2, color="tab:blue")
        ax.plot(r["model_phase"], r["model_flux"], "r-", lw=1, label=self.tr("model"))
        if self.overlay is not None:
            ax.plot(*self.overlay, "-", color="tab:green", lw=1, label=self.tr("external model"))
        ax.legend(loc="lower right")
        ax.set_ylabel(self.tr("Relative flux"))
        res.plot(r["phase"], r["residual"], ".", ms=2, color="gray")
        res.axhline(0, color="r", lw=0.8)
        res.set_xlabel(self.tr("Phase"))
        res.set_ylabel(self.tr("O−C"))
        self.plot.draw()

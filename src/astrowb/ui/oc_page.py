"""The O-C page: times of minimum, ephemeris, O-C diagram and its models."""

from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .kit.widgets import PlotCanvas, StepGuide, _title


def _decimals(err):
    """Decimals that show a value to the second significant digit of its error."""
    return max(0, 1 - int(np.floor(np.log10(err)))) if err > 0 and np.isfinite(err) else 4


class OCPage(QWidget):
    """Minimum times -> epochs, linear or quadratic ephemeris, O-C diagram."""

    ephemeris_requested = Signal(str)  # a star's name: its T0 and period from VSX (planning.ephemeris)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fit_result = None
        split = QSplitter(Qt.Horizontal, self)
        left = QWidget(self)
        lay = QVBoxLayout(left)
        lay.addWidget(_title(self.tr("O−C diagram"), self))
        self.guide = StepGuide(
            [
                (
                    self.tr("Times of minimum: measured (Minimum tab) and from the literature"),
                    self.tr(
                        "Put the times of minimum below, one per line: your own from the Minimum tab (Light curves "
                        "or Photometry window) and the published ones (Load file…; e.g. from the O−C gateway or the "
                        "papers), all in the same time scale (BJD_TDB preferably)."
                    ),
                ),
                (
                    self.tr("The ephemeris: reference T0 and period (VSX, GCVS or a paper)"),
                    self.tr(
                        "Type the star's name and press Look up (VSX), or type the period (and T0) of a published "
                        "ephemeris; it counts the cycles."
                    ),
                ),
                (
                    self.tr("Linear ephemeris first: look at the O−C diagram"),
                    self.tr(
                        "Keep Linear ephemeris and press Fit and draw O-C. Look at the diagram: a straight scatter "
                        "means a constant period; a parabola, a wave or diverging I and II minima tell you the next "
                        "model."
                    ),
                ),
                (
                    self.tr("The model the O−C shape asks for"),
                    self.tr(
                        "Parabola: Quadratic (period change). Wave: Third body (light-travel time). Primary and "
                        "secondary minima drifting apart: Apsidal motion. Fit again."
                    ),
                ),
                (
                    self.tr("Errors and the table for the paper"),
                    self.tr(
                        "For a third body or apsidal motion tick MCMC uncertainties and fit again; then Export "
                        "results (CSV / LaTeX)."
                    ),
                ),
            ],
            self,
        )
        lay.addWidget(self.guide)
        lay.addWidget(QLabel(self.tr("Minimum times, one per line: time [error] [I/II] [source]"), self))
        self.text = QPlainTextEdit(self)
        self.text.textChanged.connect(
            lambda: self.guide.set_state(0, "done" if self.text.toPlainText().strip() else None)
        )
        self.text.setPlaceholderText("2455867.40274 0.00005 I  literature\n2458107.71232 0.0033 I  this work")
        lay.addWidget(self.text, 1)
        row = QHBoxLayout()
        load = self.load_button = QPushButton(self.tr("Load file…"), self)
        load.clicked.connect(self._load)
        row.addWidget(load)
        load.setToolTip(
            self.tr("A text file of times of minimum or maximum: time, error, type (I / II), source; one per line")
        )
        row.addStretch(1)
        lay.addLayout(row)
        grid = QGridLayout()
        self.star = QLineEdit(self)
        self.star.setPlaceholderText("NY Vir")
        self.star.setToolTip(self.tr("The star's name: Look up fills T0 and the period from AAVSO VSX"))
        self.look_up = QPushButton(self.tr("Look up"), self)
        self.look_up.setToolTip(self.tr("T0 and the period of the star from AAVSO VSX (needs the internet)"))
        self.look_up.clicked.connect(self._look_up)
        self.star.returnPressed.connect(self._look_up)
        grid.addWidget(QLabel(self.tr("Star"), self), 2, 0)
        star_row = QHBoxLayout()
        star_row.addWidget(self.star, 1)
        star_row.addWidget(self.look_up)
        grid.addLayout(star_row, 2, 1)
        self.t0 = QLineEdit(self)
        self.period = QLineEdit(self)
        self.period.textChanged.connect(lambda t: self.guide.set_state(1, "done" if t.strip() else None))
        grid.addWidget(QLabel(self.tr("Reference T0"), self), 0, 0)
        self.period.setToolTip(self.tr("Period of the ephemeris used to count the cycles; the fit improves it"))
        self.t0.setToolTip(self.tr("Epoch zero of the ephemeris (BJD or HJD, as the times); empty: the first minimum"))
        grid.addWidget(self.t0, 0, 1)
        grid.addWidget(QLabel(self.tr("Period (d)"), self), 1, 0)
        grid.addWidget(self.period, 1, 1)
        lay.addLayout(grid)
        self.linear = QRadioButton(self.tr("Linear ephemeris"), self)
        self.linear.setToolTip(self.tr("A constant period: O−C on a straight line (corrects T0 and the period)"))
        self.quadratic = QRadioButton(self.tr("Quadratic (period change)"), self)
        self.quadratic.setToolTip(
            self.tr("A steadily changing period (mass transfer, mass loss): O−C on a parabola; gives dP/dt")
        )
        self.ltte = QRadioButton(self.tr("Third body (light-travel time)"), self)
        self.ltte.setToolTip(
            self.tr(
                "A third star moves the pair around: O−C waves with the third body's orbit (Irwin 1952); "
                "needs minima over more than one cycle of the wave"
            )
        )
        self.apsidal = QRadioButton(self.tr("Apsidal motion (eccentric orbit, primary and secondary)"), self)
        self.apsidal.setToolTip(
            self.tr(
                "An eccentric orbit turns: primary and secondary minima drift in opposite directions; needs"
                " both kinds of minimum (type I and II)"
            )
        )
        self.linear.setChecked(True)
        for b in (self.linear, self.quadratic, self.ltte, self.apsidal):
            lay.addWidget(b)
        row = QHBoxLayout()
        self.use_mcmc = QCheckBox(self.tr("MCMC uncertainties (slower, for correlated parameters)"), self)
        self.use_mcmc.setToolTip(
            self.tr(
                "After the fit, Markov chains explore the third-body or apsidal parameters: 68 % "
                "intervals of every parameter, e and ω included, when they depend on each other. A linear or "
                "quadratic ephemeris is a linear problem: its least-squares errors are already exact."
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

        def mcmc_allowed():
            self.use_mcmc.setEnabled(self.ltte.isChecked() or self.apsidal.isChecked())
            self.mcmc_steps.setEnabled(self.use_mcmc.isEnabled())

        for b in (self.linear, self.quadratic, self.ltte, self.apsidal):
            b.toggled.connect(mcmc_allowed)
        mcmc_allowed()
        self.fit_button = QPushButton(self.tr("Fit and draw O-C"), self)
        self.fit_button.clicked.connect(self.run_fit)
        self.fit_button.setToolTip(
            self.tr("Fits the chosen model to the times and draws O−C (observed minus calculated) against cycle number")
        )
        lay.addWidget(self.fit_button)
        from .plot.export import results_button

        self.fit_result = None
        self.background = None  # set by the main window: runs the MCMC as a task
        self.results_button = results_button(self, self.fit_table)
        lay.addWidget(self.results_button)
        self.result = QLabel(self)
        self.result.setWordWrap(True)
        self.result.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.result)
        split.addWidget(left)
        self.plot = PlotCanvas(self)
        split.addWidget(self.plot)
        split.setSizes([380, 800])
        QVBoxLayout(self).addWidget(split)

    def _load(self, path=None):
        """path: a file opened from the window's File menu or dropped on it; otherwise (a button click) asked."""
        if not isinstance(path, str):
            path, _ = QFileDialog.getOpenFileName(
                self, self.tr("Load minimum times"), "", self.tr("Text (*.txt *.csv *.dat);;All (*)")
            )
        if path:
            self.text.setPlainText(Path(path).read_text(encoding="utf-8", errors="replace"))

    def _look_up(self):
        if self.star.text().strip():
            self.result.setText(self.tr("Asking VSX…"))
            self.ephemeris_requested.emit(self.star.text().strip())

    def set_ephemeris(self, target):
        """T0 and the period from planning.ephemeris; a T0 already typed (or measured) is kept."""
        if not target.get("period"):
            self.result.setText(self.tr("{name}: no period in VSX; type it.").format(name=target.get("name", "")))
            return
        self.period.setText(repr(float(target["period"])))
        if target.get("t0") and not self.t0.text().strip():
            self.t0.setText(repr(float(target["t0"])))
        self.result.setText(
            self.tr("{name}: T0 and period from {source}. Press Fit and draw O-C.").format(
                name=target.get("name", ""), source=target.get("source", "VSX")
            )
        )

    def add_minimum(self, time, error, source="", kind="I"):
        self.text.appendPlainText(f"{time:.6f} {error:.6f} {kind} {source}".rstrip())

    def fit_table(self):
        """(rows, caption) of the last O−C fit for the results export."""
        f = self.fit_result
        if f is None:
            self.result.setText(self.tr("Fit the O−C diagram first."))
            return None
        n = len(f.epochs)
        if hasattr(f, "p3"):  # light-travel time
            e = f.errors
            rows = [
                ("T0", f.t0, e["t0"], "d"),
                ("P", f.period, e["period"], "d"),
                ("A (semi-amplitude)", f.amplitude * 1440, e["amplitude"] * 1440, "min"),
                ("P3", f.p3 / 365.25, e["p3"] / 365.25, "yr"),
                ("T3 (periastron)", f.t3, e["t3"], "d"),
                ("e3", f.e, e.get("e"), ""),
                ("omega3", f.omega, e.get("omega"), "deg"),
                ("f(m3)", f.mass_function, e.get("f_m3"), "Msun"),
            ]
            model = self.tr("light-travel time in a third-body orbit (Irwin 1952)")
        elif hasattr(f, "d_omega"):  # apsidal motion
            rows = [
                ("T0", f.t0, f.errors["t0"], "d"),
                ("Ps (sidereal)", f.period, f.errors["period"], "d"),
                ("e", f.e, f.errors.get("e"), ""),
                ("omega0", f.omega0, f.errors.get("omega0"), "deg"),
                ("d omega / dE", f.d_omega, f.errors["d_omega"], "deg/cycle"),
                ("U", f.u_years, f.errors.get("u_years"), "yr"),
            ]
            model = self.tr("apsidal motion of an eccentric orbit")
        else:
            rows = [("T0", f.t0, f.t0_err, "d"), ("P", f.period, f.period_err, "d")]
            if f.order == 2:
                rows += [("Q", f.q, f.q_err, "d"), ("dP/dt", f.dp_dt, f.dp_dt_err, "s/yr")]
            model = self.tr("quadratic ephemeris") if f.order == 2 else self.tr("linear ephemeris")
        rows.append(("chi2_r", f.chi2r, None, ""))
        caption = self.tr(
            "O−C fit to {n} times of minimum: {model}; weighted least squares, 1σ errors (scaled by √χ²ᵣ when χ²ᵣ > 1)."
        ).format(n=n, model=model)
        if getattr(f, "mcmc", None):
            caption += " " + self.tr("Errors: the larger side of the MCMC 68 % intervals (at most {s} steps).").format(
                s=self.mcmc_steps.value()
            )
        return rows, caption

    def run_fit(self):
        from ..timeseries.ephemeris import fit, parse_minima
        from ..timeseries.oc_models import fit_apsidal, fit_ltte
        from .messages import translate

        try:
            period = float(self.period.text())
        except ValueError:
            self.result.setText(self.tr("Give the period in days, or the star's name and Look up."))
            return None
        try:
            minima = parse_minima(self.text.toPlainText())
            try:
                t0 = float(self.t0.text())
            except ValueError:  # empty: the first primary minimum, as the tooltip says
                t0 = min((m.time for m in minima if m.kind == "I"), default=minima[0].time if minima else float("nan"))
            steps = self.mcmc_steps.value() if self.use_mcmc.isChecked() and self.use_mcmc.isEnabled() else 0
            model = "ltte" if self.ltte.isChecked() else "apsidal" if self.apsidal.isChecked() else None
            if steps and self.background:  # the chain runs as a task: the page stays usable, Tasks can cancel it
                self.result.setText(self.tr("Fitting, then the MCMC ({s} steps) runs as a task…").format(s=steps))
                self.background(model, self.text.toPlainText(), t0, period, steps, minima)
                return None
            if model == "ltte":
                f = fit_ltte(minima, t0, period, mcmc_steps=steps)
            elif model == "apsidal":
                f = fit_apsidal(minima, t0, period, mcmc_steps=steps)
            else:
                f = fit(minima, t0, period, order=2 if self.quadratic.isChecked() else 1)
        except ValueError as e:
            self.result.setText(self.tr("Cannot fit: {error}").format(error=translate(str(e))))
            return None
        return self.show_fit(f, minima)

    def show_fit(self, f, minima):
        """Draw a fit (also the result of the background task) and write its numbers."""
        self.fit_result = f
        self.guide.set_state(2, "done")
        if getattr(f, "order", 2) != 1:  # a model beyond the straight line
            self.guide.set_state(3, "done")
        if getattr(f, "mcmc", None):
            self.guide.set_state(4, "done")
        if not hasattr(f, "order"):
            return self._show_oc_model(f, minima)
        lines = [
            self.tr("T0 = {t0:.6f} ± {e:.6f}").format(t0=f.t0, e=f.t0_err),
            self.tr("P = {p:.8f} ± {e:.8f} d").format(p=f.period, e=f.period_err),
        ]
        if f.order == 2:
            lines.append(
                self.tr("Q = {q:.3e} ± {e:.1e} d, dP/dt = {dp:.3g} ± {dpe:.2g} s/yr").format(
                    q=f.q, e=f.q_err, dp=f.dp_dt, dpe=f.dp_dt_err
                )
            )
        lines.append(self.tr("χ²ᵣ = {c:.2f}, {n} minima").format(c=f.chi2r, n=len(minima)))
        self.result.setText("\n".join(lines))
        errs = np.array([m.error or np.nan for m in minima])
        self.plot.figure.clear()
        ax, ax2 = self.plot.figure.subplots(2, 1, sharex=True, height_ratios=[3, 1])
        prim = np.array([m.kind == "I" for m in minima])
        for sel, label, mk in ((prim, self.tr("primary"), "o"), (~prim, self.tr("secondary"), "s")):
            if sel.any():
                ax.errorbar(f.epochs[sel], f.o_minus_c[sel] * 1440, errs[sel] * 1440, fmt=mk, ms=4, label=label)
        e_line = np.linspace(f.epochs.min(), f.epochs.max(), 200)
        ax.plot(e_line, f.model_o_minus_c(e_line) * 1440, "r-", lw=1)
        ax.set_ylabel(self.tr("O−C (min)"))
        ax.legend(fontsize="small")
        ax2.errorbar(f.epochs, f.residuals * 1440, errs * 1440, fmt=".", ms=3)
        ax2.axhline(0, color="r", lw=1)
        ax2.set_xlabel(self.tr("Epoch"))
        ax2.set_ylabel(self.tr("Residual (min)"))
        self.plot.draw()
        return f

    def _oc_model_text(self, f, n):
        if hasattr(f, "p3"):
            return [
                self.tr(
                    "Third body: P3 = {p:.2f} ± {pe:.2f} yr, A = {a:.2f} ± {ae:.2f} min, e = {e:.2f}, ω = {w:.0f}°"
                ).format(
                    p=f.p3 / 365.25,
                    pe=f.errors["p3"] / 365.25,
                    a=f.amplitude * 1440,
                    ae=f.errors["amplitude"] * 1440,
                    e=f.e,
                    w=f.omega,
                ),
                self.tr("f(m3) = {fm:.4f} M☉, T0 = {t0:.6f}, P = {p:.8f} d, χ²ᵣ = {c:.2f}, {n} minima").format(
                    fm=f.mass_function, t0=f.t0, p=f.period, c=f.chi2r, n=n
                ),
            ]
        return [
            self.tr(
                "Apsidal motion: e = {e:.4f}, ω0 = {w:.1f}°, dω/dE = {dw:.5f} ± {dwe:.5f} °/cycle, U = {u:.1f} yr"
            ).format(e=f.e, w=f.omega0, dw=f.d_omega, dwe=f.errors["d_omega"], u=f.u_years),
            self.tr("T0 = {t0:.6f}, Ps = {p:.8f} d, χ²ᵣ = {c:.2f}, {n} minima").format(
                t0=f.t0, p=f.period, c=f.chi2r, n=n
            ),
        ]

    def _show_oc_model(self, f, minima):
        """Third body or apsidal motion: the curve(s) over the O-C points, residuals below."""
        lines = self._oc_model_text(f, len(minima))
        if f.mcmc:
            p = f.mcmc["params"]
            shown = [("e", "e", 1), ("ω", "omega", 1), ("ω0", "omega0", 1), ("U", "u_years", 1)]
            shown += [("P3", "p3", 1 / 365.25), ("A", "amplitude", 1440), ("f(m3)", "f_m3", 1)]
            lines.append(
                self.tr("MCMC (acceptance {a:.2f}): ").format(a=f.mcmc["acceptance"])
                + ", ".join(
                    f"{label} = {p[k][0] * u:.{_decimals(min(p[k][1:]) * u)}f} −{p[k][1] * u:.2g} +{p[k][2] * u:.2g}"
                    for label, k, u in shown
                    if k in p
                )
            )
        self.result.setText("\n".join(lines))
        errs = np.array([m.error or np.nan for m in minima])
        prim = np.array([m.kind == "I" for m in minima])
        self.plot.figure.clear()
        ax, ax2 = self.plot.figure.subplots(2, 1, sharex=True, height_ratios=[3, 1])
        e_line = np.linspace(f.epochs.min(), f.epochs.max(), 600)
        for sel, label, mk, kind in ((prim, self.tr("primary"), "o", "I"), (~prim, self.tr("secondary"), "s", "II")):
            if sel.any():
                ax.errorbar(f.epochs[sel], f.o_minus_c[sel] * 1440, errs[sel] * 1440, fmt=mk, ms=4, label=label)
                ax.plot(e_line, f.model_o_minus_c(e_line, kind) * 1440, lw=1)
        ax.set_ylabel(self.tr("O−C (min)"))
        ax.legend(fontsize="small")
        ax2.errorbar(f.epochs, f.residuals * 1440, errs * 1440, fmt=".", ms=3)
        ax2.axhline(0, color="r", lw=1)
        ax2.set_xlabel(self.tr("Epoch"))
        ax2.set_ylabel(self.tr("Residual (min)"))
        self.plot.draw()
        return f

"""Visual binary orbit: position angles and separations in, Campbell elements, plot and ephemeris out."""

import numpy as np
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class VisualOrbitTab(QWidget):
    fit_requested = Signal(dict, dict)

    def __init__(self, parent=None):
        from PySide6.QtCore import Qt

        from .kit.widgets import PlotCanvas

        super().__init__(parent)
        self.orbit = None
        split = QSplitter(Qt.Horizontal, self)
        left = QWidget(self)
        lay = QVBoxLayout(left)
        hint = QLabel(
            self.tr("Measures, one per line: epoch (year)  position angle (°)  separation (″)  [σ″]  [σ°]"), self
        )
        hint.setWordWrap(True)  # long in some languages: wraps instead of widening the page
        lay.addWidget(hint)
        self.measures = QPlainTextEdit(self)
        self.measures.setPlaceholderText("2001.512  128.4  0.512  0.005  0.5")
        lay.addWidget(self.measures, 1)
        load = self.load_button = QPushButton(self.tr("Load measures…"), self)
        load.clicked.connect(self._load)
        load.setToolTip(self.tr("A text file of measures (e.g. from the WDS / Sixth Orbit Catalog), one per line"))
        lay.addWidget(load)
        grid = QGridLayout()
        self.p_min, self.p_max, self.parallax = QDoubleSpinBox(self), QDoubleSpinBox(self), QDoubleSpinBox(self)
        for w, top in ((self.p_min, 100000.0), (self.p_max, 100000.0), (self.parallax, 2000.0)):
            w.setRange(0.0, top)
            w.setDecimals(3)
            w.setSpecialValueText(self.tr("automatic"))
        self.parallax.setSpecialValueText(self.tr("not given"))
        self.parallax.setToolTip(
            self.tr("With the parallax (e.g. from Gaia) the total mass of the pair follows from Kepler's third law")
        )
        self.p_max.setToolTip(self.tr("Range of periods searched; automatic: from the time span of the measures"))
        self.p_min.setToolTip(self.tr("Range of periods searched; automatic: from the time span of the measures"))
        for r, (label, w) in enumerate(
            (
                (self.tr("Shortest period (years)"), self.p_min),
                (self.tr("Longest period (years)"), self.p_max),
                (self.tr("Parallax (mas, for the mass)"), self.parallax),
            )
        ):
            grid.addWidget(QLabel(label, self), r, 0)
            grid.addWidget(w, r, 1)
        lay.addLayout(grid)
        self.fit_button = QPushButton(self.tr("Fit the orbit"), self)
        self.fit_button.clicked.connect(self._fit)
        self.fit_button.setToolTip(
            self.tr(
                "Fits the seven orbital elements (P, T, e, a, i, Ω, ω) to the measures and draws the apparent orbit"
            )
        )
        lay.addWidget(self.fit_button)
        self.table = QTableWidget(0, 2, self)
        self.table.setHorizontalHeaderLabels([self.tr("Element"), self.tr("Value")])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().hide()
        lay.addWidget(self.table, 1)
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        split.addWidget(left)
        self.plot = PlotCanvas(self)
        split.addWidget(self.plot)
        split.setSizes([420, 780])
        QVBoxLayout(self).addWidget(split)

    def _load(self):
        path, _ = QFileDialog.getOpenFileName(self, self.tr("Load measures"), "", "Text (*.txt *.dat *.csv);;All (*)")
        if path:
            with open(path, encoding="utf-8", errors="replace") as f:
                self.measures.setPlainText(f.read())

    def params(self):
        out = {}
        if self.p_min.value() and self.p_max.value():
            out |= {"p_min": self.p_min.value(), "p_max": self.p_max.value()}
        if self.parallax.value():
            out["parallax_mas"] = self.parallax.value()
        return out

    def _fit(self):
        if not self.measures.toPlainText().strip():
            self.status.setText(self.tr("Type or load the measures first."))
            return
        self.status.setText(self.tr("Fitting…"))
        self.fit_requested.emit({"measures": self.measures.toPlainText()}, self.params())

    def show_orbit(self, o):
        from ..models import visual

        self.orbit = o
        err = o["errors"]
        rows = [
            (self.tr("Period P (years)"), f"{o['P']:.4f} ± {err['P']:.4f}"),
            (self.tr("Periastron T (year)"), f"{o['T']:.4f} ± {err['T']:.4f}"),
            (self.tr("Eccentricity e"), f"{o['e']:.4f} ± {err['e']:.4f}"),
            (self.tr("Semi-major axis a (″)"), f"{o['a']:.4f} ± {err['a']:.4f}"),
            (self.tr("Inclination i (°)"), f"{o['i']:.2f} ± {err['i']:.2f}"),
            (self.tr("Node Ω (°)"), f"{o['node']:.2f} ± {err['node']:.2f}"),
            (self.tr("Periastron argument ω (°)"), f"{o['omega']:.2f} ± {err['omega']:.2f}"),
            (self.tr("Reduced χ²"), f"{o['chi2_red']:.2f}"),
            (self.tr("rms of the separations (″)"), f"{o['rms_rho']:.4f}"),
        ]
        if "mass" in o:
            rows.append((self.tr("Total mass (M☉)"), f"{o['mass']:.3f} ± {o['mass_err']:.3f}"))
        self.table.setRowCount(len(rows))
        for r, (k, v) in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(k))
            self.table.setItem(r, 1, QTableWidgetItem(v))
        self.status.setText(
            self.tr("{n} measures. Ω and ω can both be turned by 180° without radial velocities.").format(n=o["n"])
        )
        A, B, F, G = o["thiele_innes"]
        ts = o["T"] + np.linspace(0, o["P"], 721)
        north, east = visual.xy_of(ts, o["P"], o["T"], o["e"], A, B, F, G)
        on, oe = visual.to_xy(o["theta"], o["rho"])
        cn, ce = visual.xy_of(np.asarray(o["epoch"]), o["P"], o["T"], o["e"], A, B, F, G)
        self.plot.figure.clear()
        ax = self.plot.figure.add_subplot()
        ax.plot(east, north, "-", lw=1, label=self.tr("orbit"))
        ax.plot(oe, on, "o", ms=3, label=self.tr("measures"))
        for a, b, c, d in zip(oe, on, ce, cn, strict=True):
            ax.plot([a, c], [b, d], "-", color="#e5484d", lw=0.6)  # O - C
        ax.plot([0], [0], "*", color="orange", ms=12, label=self.tr("primary"))
        ax.set_aspect("equal", adjustable="datalim")
        ax.invert_xaxis()  # east to the left, as on the sky
        ax.set_xlabel(self.tr("East (″)"))
        ax.set_ylabel(self.tr("North (″)"))
        ax.legend(fontsize=7)
        self.plot.draw()

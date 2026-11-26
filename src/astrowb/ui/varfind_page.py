"""Variable-star search tab (as Muniwin's varfind): every star of the field measured on every frame, the
magnitude-scatter diagram with the candidates marked, and any star's light curve one click away."""

import numpy as np
from astropy.table import Table
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..photometry.varperiod import KNOWN, known_columns
from .files import images_filter
from .kit import tokens
from .kit.help import help_line
from .kit.table import TableView
from .plot.spec import AxisSpec, FigureSpec, PanelSpec, SeriesSpec
from .plot.toolbar import plot_box

FITS = "FITS (*.fits *.fit *.fts *.FITS *.FIT)"


class VarFindPage(QWidget):
    search_requested = Signal(list, dict)  # images, params
    light_curve_chosen = Signal(list, list, str)  # time, relative flux, label (to the Period search tab)
    known_requested = Signal(str)  # the first frame, solved and its catalogues asked (varfind_export.look_up)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.images, self.result, self.star = [], None, None
        split = QSplitter(Qt.Horizontal, self)
        left = QWidget(self)
        lay = QVBoxLayout(left)
        from .kit.widgets import StepGuide

        self.guide = StepGuide(
            [
                (
                    self.tr("Choose calibrated frames of one field"),
                    self.tr("Press Choose frames…; the stars are found on the first frame."),
                ),
                (
                    self.tr("Search for variables: each star's scatter against stars of its brightness"),
                    self.tr("Press Search for variables."),
                ),
                (
                    self.tr("Check the candidates"),
                    self.tr(
                        "Click a candidate in the plot to see its light curve: a real variable changes smoothly; a "
                        "star that jumps at one frame or lies at the edge is a measuring problem."
                    ),
                ),
                (self.tr("Find its period"), self.tr("Press Send this star to Period search.")),
            ],
            self,
        )
        lay.addWidget(self.guide)
        note = self.tr("Stars that scatter more than others of their brightness are candidates. Use calibrated frames.")
        info = help_line(note, "photometry-psf-photometry-searching-variables", self)
        lay.addWidget(info)
        choose = self.choose_button = QPushButton(self.tr("Choose frames…"), self)
        choose.clicked.connect(
            lambda: self.set_images(QFileDialog.getOpenFileNames(self, self.tr("Frames"), "", images_filter())[0])
        )
        choose.setToolTip(self.tr("The calibrated frames of one field, taken over a night or more"))
        lay.addWidget(choose)
        self.source = QLabel(self.tr("No frames."), self)
        lay.addWidget(self.source)
        form = QFormLayout()
        self.method = QComboBox(self)
        self.method.addItem(self.tr("Aperture photometry"), "aperture")
        self.method.addItem(self.tr("PSF photometry (crowded fields)"), "psf")
        self.method.setToolTip(
            self.tr("Aperture photometry for most fields; PSF photometry where the stars overlap (slower)")
        )
        self.max_stars = QSpinBox(self)
        self.max_stars.setRange(10, 5000)
        self.max_stars.setValue(300)
        self.max_stars.setToolTip(
            self.tr("How many of the brightest stars in the field are measured; more stars take longer")
        )
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
        self.button.setToolTip(
            self.tr(
                "Measures every star in every frame against all the others and lists those that vary more "
                "than stars of the same brightness"
            )
        )
        lay.addWidget(self.button)
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        self.table = TableView(self)
        self.stars = []  # the star index of every table row
        self._set_stars([])
        self.table.row_chosen.connect(lambda r: self.show_star(self.stars[r]))
        lay.addWidget(self.table, 1)
        self.send = QPushButton(self.tr("Send this star to Period search"), self)
        self.send.setEnabled(False)
        self.send.clicked.connect(self._send)
        self.send.setToolTip(self.tr("The chosen star's light curve goes to the Period search tab"))
        lay.addWidget(self.send)
        split.addWidget(left)
        box, self.plot = plot_box(self)
        self.plot.point_clicked.connect(self._clicked)
        split.addWidget(box)
        split.setSizes([420, 800])
        QVBoxLayout(self).addWidget(split)

    def _set_stars(self, rows, known=None):
        """The candidates' table; known: varperiod.known_columns for the same rows (empty columns without it)."""
        names = (
            self.tr("x"),
            self.tr("y"),
            self.tr("Magnitude"),
            self.tr("rms (mag)"),
            self.tr("Index"),
            self.tr("Flags"),
            self.tr("Period (d)"),
            self.tr("Power"),
        )
        table = Table(list(np.asarray(rows, float).reshape(-1, 8).T), names=names)
        for col in table.columns.values():
            col.format = ".4g"
        table[names[5]].description = self.tr(
            "How many of six variability indices (σ, MAD, IQR, 1/η, Stetson J, χ²) set the star apart"
        )
        k = known or {key: [empty] * len(table) for key, empty in KNOWN.items()}
        period = [f"{p:.6g}" if np.isfinite(p) else "" for p in k["vsx_period_d"]]
        for name, values in ((self.tr("VSX"), k["vsx"]), (self.tr("Type"), k["vsx_type"]),
                             (self.tr("VSX period (d)"), period), (self.tr("GCVS"), k["gcvs"]),
                             (self.tr("Gaia"), k["gaia_variable"])):  # fmt: skip
            table[name] = np.asarray(values, str)
        self.table.set_table(table)

    def set_images(self, paths):
        from ..io.bayer import fits_paths

        self.images = fits_paths(paths)  # camera raw files and pictures get a FITS copy
        self.source.setText(self.tr("{n} frames").format(n=len(self.images)))
        self.button.setEnabled(len(self.images) >= 5)
        self.guide.reset()
        self.guide.set_state(0, "done")

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
        self.guide.set_state(1, "done")
        v = out["variability"]
        xy = np.asarray(out["field"]["xy"])
        cand = np.flatnonzero(v["candidate"])
        flags = np.asarray(v.get("flags") or np.zeros(len(xy)))
        order = cand[np.lexsort((-np.asarray(v["index"])[cand], -flags[cand]))]  # most indices first
        self.stars = [int(j) for j in order]
        q = out.get("candidate_periods") or {"star": [], "period": [], "power": []}  # the quick GLS per candidate
        at = {s: (p, w) for s, p, w in zip(q["star"], q["period"], q["power"], strict=True)}
        nan = (np.nan, np.nan)
        self._set_stars(
            [
                (xy[j, 0], xy[j, 1], v["mean"][j], v["rms"][j], v["index"][j], flags[j], *at.get(int(j), nan))
                for j in order
            ],
            known_columns(out, self.stars),
        )
        self.status.setText(self.tr("{n} stars measured, {m} candidates.").format(n=len(xy), m=len(order)))
        self.show_star(int(order[0]) if len(order) else None)

    def show_star(self, j):
        self.star = j
        self.guide.set_state(2, "done")
        v = self.result["variability"]
        mean, rms = np.asarray(v["mean"]), np.asarray(v["rms"])
        cand = np.asarray(v["candidate"])
        order = np.argsort(mean)
        halo, red = tokens.role("comparison"), tokens.role("target")
        stars = [
            SeriesSpec(self.tr("stars"), mean, rms, size=5, pickable=True),
            # a ring round each candidate (a halo behind the dot: the plot has no hollow symbols)
            SeriesSpec(self.tr("candidates"), mean[cand], rms[cand], size=10, alpha=0.4, colour=halo),
            SeriesSpec(self.tr("typical rms"), mean[order], np.asarray(v["typical"])[order], kind="line", width=0.8),
        ]
        curve, x_label, y_label = [], "", ""
        if j is not None:
            stars.append(SeriesSpec(self.tr("chosen star"), [mean[j]], [rms[j]], symbol="*", size=14, colour=red))
            t = np.asarray(self.result["field"]["time"])
            m = np.asarray(v["corrected"])[:, j]
            curve = [SeriesSpec(self.tr("Magnitude"), t - np.floor(t.min()), m, size=4)]
            x_label, y_label = self.tr("JD − {d:.0f}").format(d=np.floor(t.min())), self.tr("Magnitude")
        top = PanelSpec(AxisSpec(self.tr("Instrumental magnitude")), AxisSpec(self.tr("rms (mag)"), scale="log"), stars)
        self.plot.set_figure(
            FigureSpec([top, PanelSpec(AxisSpec(x_label), AxisSpec(y_label, invert=True), curve)], shared_x=False)
        )
        self.send.setEnabled(j is not None)

    def _clicked(self, name, j):
        """A click on a star of the scatter shows its light curve (after this click: the plot is redrawn)."""
        if self.result is not None and name == self.tr("stars"):
            QTimer.singleShot(0, lambda: self.show_star(int(j)))

    def _send(self):
        self.guide.set_state(3, "done")
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

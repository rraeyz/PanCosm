"""The Photometry window's PSF results tab (plans/photometry.md PHO-18): the effective PSF of the last PSF run (the
reference frame's isolated stars, photometry.psf.epsf_summary), the stars it was built from, its quality number and
the chosen star's residual (its stamp minus the fitted ePSF); a chosen star can be left out of the PSF, which measures
again with the step's psf_exclude."""

import numpy as np
from astropy.table import Table
from PySide6.QtCore import QCoreApplication, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .kit.table import TableView
from .viewer import ImageViewer

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PhotometryPsf", "…") calls


def attach(page):
    page.psf_tab = PsfTab(page)
    page.res_tabs.addTab(page.psf_tab, translate("PhotometryPsf", "PSF"))
    page.psf_tab.exclude_changed.connect(page._measure)  # photometry_method.method_params passes the list on


class PsfTab(QWidget):
    exclude_changed = Signal()  # self.exclude changed: measure again

    def __init__(self, parent=None):
        super().__init__(parent)
        self.note = QLabel(self)
        self.note.setWordWrap(True)
        self.view = ImageViewer(self)
        self.view.empty_hint = translate("PhotometryPsf", "Measure with PSF photometry to see the PSF.")
        self.residual = ImageViewer(self)
        self.residual.empty_hint = translate("PhotometryPsf", "Choose a PSF star to see its residual.")
        self.residual.setToolTip(translate("PhotometryPsf", "The chosen star's stamp minus the fitted PSF."))
        self.stars = TableView(self)
        self.stars.row_chosen.connect(self._show_residual)
        self.residuals, self.rows, self.exclude, self.row = [], [], [], -1
        self.leave_out = QPushButton(translate("PhotometryPsf", "Leave out this star"), self)
        self.leave_out.setToolTip(translate("PhotometryPsf", "Build the PSF again without the chosen star."))
        self.leave_out.clicked.connect(self._leave_out)
        self.use_all = QPushButton(translate("PhotometryPsf", "Use all stars again"), self)
        self.use_all.clicked.connect(self._use_all)
        buttons = QHBoxLayout()
        buttons.addWidget(self.leave_out)
        buttons.addWidget(self.use_all)
        buttons.addStretch(1)
        images = QHBoxLayout()
        images.addWidget(self.view, 1)
        images.addWidget(self.residual, 1)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.note)
        lay.addLayout(images, 1)
        lay.addWidget(self.stars, 1)
        lay.addLayout(buttons)
        self.show_psf(None)

    def _leave_out(self):
        if 0 <= self.row < len(self.rows):
            self.exclude.append(self.rows[self.row][:2])
            self.exclude_changed.emit()

    def _use_all(self):
        self.exclude = []
        self.exclude_changed.emit()

    def _show_residual(self, row):
        self.row = row
        if 0 <= row < len(self.residuals):
            self.residual.set_image(np.asarray(self.residuals[row], float))

    def _show_stars(self, info):
        """The PSF stars' table and the first star's residual; empty without them."""
        self.rows = rows = info.get("stars") or []
        self.residuals = info.get("residuals") or []
        self.leave_out.setEnabled(bool(rows))
        self.use_all.setEnabled(bool(self.exclude))
        names = ("x", "y", "peak", "residual_pct")
        t = Table(rows=rows, names=names) if rows else Table(names=names)
        for name, unit in zip(names, ("pix", "pix", "adu", "%"), strict=True):
            t[name].unit = unit
        self.stars.set_table(t)
        self.residual.clear()
        self._show_residual(0)

    def show_psf(self, lc):
        """The ePSF picture and the stars count from a light curve; nothing when it was not a PSF run."""
        info = (lc or {}).get("psf")
        self._show_stars(info or {})
        self.note.setToolTip("")
        if not info:
            self.view.clear()
            self.note.setText(translate("PhotometryPsf", "No PSF run yet."))
            return
        if info["epsf"] is None:
            self.view.clear()
            self.note.setText(
                translate("PhotometryPsf", "Too few isolated stars for a PSF picture: {n} found.").format(
                    n=info["n_stars"]
                )
            )
            return
        self.view.set_image(np.asarray(info["epsf"], float))
        text = translate("PhotometryPsf", "Effective PSF of {n} stars, oversampled {k} times.").format(
            n=info["n_stars"], k=info["oversampling"]
        )
        if info.get("quality") is not None:
            text += " " + translate("PhotometryPsf", "Quality: residual {q:.2f} % of the peak.").format(
                q=info["quality"]
            )
            self.note.setToolTip(
                translate(
                    "PhotometryPsf",
                    "The RMS of the PSF stars' stamps minus the fitted PSF, in per cent of each star's peak:"
                    " smaller is a better PSF.",
                )
            )
        self.note.setText(text)

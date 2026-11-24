"""The Photometry window's PSF results tab (plans/photometry.md PHO-18): the effective PSF of the last PSF run (the
reference frame's isolated stars, photometry.psf.epsf_summary), the stars it was built from, its quality number and
the chosen star's residual (its stamp minus the fitted ePSF)."""

import numpy as np
from astropy.table import Table
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .kit.table import TableView
from .viewer import ImageViewer

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PhotometryPsf", "…") calls


def attach(page):
    page.psf_tab = PsfTab(page)
    page.res_tabs.addTab(page.psf_tab, translate("PhotometryPsf", "PSF"))


class PsfTab(QWidget):
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
        self.residuals = []
        images = QHBoxLayout()
        images.addWidget(self.view, 1)
        images.addWidget(self.residual, 1)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.note)
        lay.addLayout(images, 1)
        lay.addWidget(self.stars, 1)
        self.show_psf(None)

    def _show_residual(self, row):
        if 0 <= row < len(self.residuals):
            self.residual.set_image(np.asarray(self.residuals[row], float))

    def _show_stars(self, info):
        """The PSF stars' table and the first star's residual; empty without them."""
        rows = info.get("stars") or []
        self.residuals = info.get("residuals") or []
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

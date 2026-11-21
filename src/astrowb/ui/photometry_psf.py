"""The Photometry window's PSF results tab (plans/photometry.md PHO-18): the effective PSF of the last PSF run (the
reference frame's isolated stars, photometry.psf.epsf_summary) and how many stars made it."""

import numpy as np
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

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
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.note)
        lay.addWidget(self.view, 1)
        self.show_psf(None)

    def show_psf(self, lc):
        """The ePSF picture and the stars count from a light curve; nothing when it was not a PSF run."""
        info = (lc or {}).get("psf")
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
        self.note.setText(
            translate("PhotometryPsf", "Effective PSF of {n} stars, oversampled {k} times.").format(
                n=info["n_stars"], k=info["oversampling"]
            )
        )

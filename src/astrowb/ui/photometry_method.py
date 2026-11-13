"""The measuring method of the Photometry window (plans/photometry.md PHO-18): apertures, PSF fits, or apertures
after the neighbours are fitted and subtracted. Two check boxes that exclude each other."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QCheckBox

translate = QCoreApplication.translate  # the strings keep the PhotometryPage context they had there


def add_method_boxes(page, body):
    """page.psf and page.remove_neighbours, added to body."""
    page.psf = QCheckBox(translate("PhotometryPage", "PSF photometry (crowded fields: blended stars fitted together)"))
    page.psf.setToolTip(
        translate(
            "PhotometryPage",
            "For crowded fields: stars that overlap are fitted together with the image's star profile "
            "instead of being added up in a circle. Slower; for isolated stars the aperture is as good.",
        )
    )
    page.remove_neighbours = QCheckBox(translate("PhotometryPage", "Remove neighbours, then measure in apertures"))
    page.remove_neighbours.setToolTip(
        translate(
            "PhotometryPage",
            "Stars close to the measured ones are found on the first frame, fitted on every frame and subtracted "
            "before the apertures are summed: the target's own light is still an aperture sum.",
        )
    )
    for box, other in ((page.psf, page.remove_neighbours), (page.remove_neighbours, page.psf)):
        box.toggled.connect(lambda on, other=other: on and other.setChecked(False))
        body.addWidget(box)

"""The measuring method of the Photometry window (plans/photometry.md PHO-18): apertures, PSF fits, or apertures
after the neighbours are fitted and subtracted. Two check boxes that exclude each other."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton

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
    row = QHBoxLayout()  # PHO-44
    row.addWidget(QLabel(translate("PhotometryPage", "Centring"), page))
    page.centring = QComboBox(page)
    for key, text in (("auto", translate("PhotometryPage", "1-D Gaussians (default)")),
                      ("gauss", translate("PhotometryPage", "2-D Gaussian (most precise, slower)")),
                      ("moments", translate("PhotometryPage", "centre of light (IRAF centroid)")),
                      ("none", translate("PhotometryPage", "none: the positions follow the field"))):  # fmt: skip
        page.centring.addItem(text, key)
    page.centring.setToolTip(
        translate(
            "PhotometryPage",
            "How each star is found on every frame. The 2-D Gaussian is the most precise (about 3 % less scatter on "
            "small, sharp stars) but about a quarter slower; the default is fast and good enough for most nights.",
        )
    )
    row.addWidget(page.centring, 1)
    body.addLayout(row)
    track = QHBoxLayout()  # the owner: the frames placed on stars the user picks, when the automatic way cannot
    track.addWidget(QLabel(translate("PhotometryPage", "Place the frames on"), page))
    page.track_stars = QLineEdit(page)
    page.track_stars.setPlaceholderText(translate("PhotometryPage", "automatic (the whole frame's shift)"))
    page.track_stars.setToolTip(
        translate(
            "PhotometryPage",
            "Stars picked on the first frame (x y; x y …) that every frame is placed on: one "
            "gives the shift, two or more the rotation too. Empty: automatic",
        )  # fmt: skip
    )
    pick = page.pick_track_stars = QPushButton(translate("PhotometryPage", "Pick stars…"), page)
    pick.clicked.connect(lambda: _pick_track(page))
    track.addWidget(page.track_stars, 1)
    track.addWidget(pick)
    body.addLayout(track)


def _pick_track(page):
    from .star_picker import StarPicker, as_text, parse

    if not page.images:
        return
    try:
        stars = parse(page.track_stars.text())
    except ValueError:
        stars = []
    dlg = StarPicker(page.images[0], stars, page)
    if dlg.exec():
        page.track_stars.setText(as_text(dlg.stars))


def method_params(page):
    """The method settings for the light-curve step and the live light curve alike."""
    return {
        "psf": page.psf.isChecked(),
        "remove_neighbours": page.remove_neighbours.isChecked(),
        "sky_method": page.sky_method.currentData(),
        "centring": page.centring.currentData(),
        "track_stars": _track(page),
    }


def _track(page):
    from .star_picker import parse

    try:
        return [list(s) for s in parse(page.track_stars.text())]
    except ValueError:  # unreadable: placed automatically, as with the field empty
        return []

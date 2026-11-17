"""The Apertures stage's shape choice (plans/photometry.md PHO-22): circle (the default) or an ellipse whose axis ratio
and angle are typed or read from a star's second moments (photometry.shapes.moments_shape)."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton, QWidget

translate = QCoreApplication.translate


def add_shape_controls(page, body):
    page.shape_kind = QComboBox(page)
    page.shape_kind.addItem(translate("PhotometryShape", "Circle"), "circle")
    page.shape_kind.addItem(translate("PhotometryShape", "Ellipse"), "ellipse")
    page.shape_kind.setToolTip(
        translate(
            "PhotometryShape",
            "The form of the aperture and of the sky ring: a circle, or an ellipse for stars stretched by tracking "
            "or optics. Ring 1–3 are then the major semi-axes.",
        )
    )
    page.shape_ratio = QDoubleSpinBox(page)
    page.shape_ratio.setRange(0.1, 1.0)
    page.shape_ratio.setSingleStep(0.05)
    page.shape_ratio.setValue(1.0)
    page.shape_angle = QDoubleSpinBox(page)
    page.shape_angle.setRange(-90.0, 90.0)
    page.shape_angle.setSuffix("°")
    page.shape_read = QPushButton(translate("PhotometryShape", "Read from the star"), page)
    page.shape_read.setToolTip(
        translate(
            "PhotometryShape",
            "Measures the axis ratio and the angle of the selected star (the target when none is selected) on the "
            "first frame.",
        )
    )
    page.shape_read.clicked.connect(lambda: read_from_star(page))
    row = QHBoxLayout()
    row.addWidget(QLabel(translate("PhotometryShape", "Aperture shape"), page))
    row.addWidget(page.shape_kind, 1)
    body.addLayout(row)
    page.shape_ellipse = QWidget(page)
    lay = QHBoxLayout(page.shape_ellipse)
    lay.setContentsMargins(0, 0, 0, 0)
    for label, w in ((translate("PhotometryShape", "Axis ratio"), page.shape_ratio),
                     (translate("PhotometryShape", "Angle"), page.shape_angle)):  # fmt: skip
        lay.addWidget(QLabel(label, page))
        lay.addWidget(w)
    lay.addWidget(page.shape_read)
    body.addWidget(page.shape_ellipse)
    page.shape_kind.currentIndexChanged.connect(lambda *_: _changed(page))
    _changed(page)


def _changed(page):
    page.shape_ellipse.setVisible(page.shape_kind.currentData() == "ellipse")
    if hasattr(page, "star_table"):
        page._fill_star_table()


def shape_params(page):
    """The `aperture_shape` step parameter: None for circles."""
    if page.shape_kind.currentData() != "ellipse":
        return None
    return {"kind": "ellipse", "ratio": page.shape_ratio.value(), "angle": page.shape_angle.value()}


def shape_text(page):
    s = shape_params(page)
    if s is None:
        return translate("PhotometryShape", "circle")
    return translate("PhotometryShape", "ellipse {ratio:.2f}, {angle:.0f}°").format(**s)


def read_from_star(page):
    """Fills the ratio and angle from the selected star (else the target) on the first frame."""
    from ..calibration.masters import load
    from ..photometry.shapes import moments_shape

    stars = page._star_names()
    row = page.star_table.currentRow()
    xy = stars[row][2] if 0 <= row < len(stars) else page.target
    if not page.images or xy is None:
        page.result.setText(translate("PhotometryShape", "Choose the images and click a star first."))
        return
    data = load(page.images[page.ref or 0])[0]
    ratio, angle = moments_shape(data, xy[0], xy[1], page.r_ap.value())
    page.shape_ratio.setValue(ratio)
    page.shape_angle.setValue(max(-90.0, min(90.0, angle)))
    _changed(page)

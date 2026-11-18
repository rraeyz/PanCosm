"""Painted pixels for the Apertures stage's Shape choice (plans/photometry.md PHO-22): clicks (and the Area tool's
rectangle) toggle the pixels of the target's mask; every other star gets the same pixels around itself."""

import numpy as np
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from .image.layers import Box

translate = QCoreApplication.translate


def add_paint_controls(page, body):
    page.paint_pixels = set()  # (dx, dy) from the target's pixel at the first paint
    page.paint_anchor = None
    page.shape_paint = QWidget(page)
    lay = QHBoxLayout(page.shape_paint)
    lay.setContentsMargins(0, 0, 0, 0)
    page.paint_clear = QPushButton(translate("PhotometryPaint", "Clear"), page)
    page.paint_clear.setToolTip(translate("PhotometryPaint", "Takes every painted pixel off."))
    page.paint_clear.clicked.connect(lambda: clear(page))
    page.paint_threshold = QPushButton(translate("PhotometryPaint", "From threshold"), page)
    page.paint_threshold.setToolTip(
        translate(
            "PhotometryPaint",
            "Paints the connected pixels of the target that stand 3 sigma above the sky. Click or drag (Area tool) "
            "on the image to add or take off pixels.",
        )
    )
    page.paint_threshold.clicked.connect(lambda: from_threshold(page))
    lay.addWidget(page.paint_clear)
    lay.addWidget(page.paint_threshold)
    body.addWidget(page.shape_paint)
    page.viewer.region_selected.connect(lambda x0, y0, x1, y1: paint_rect(page, x0, y0, x1, y1))


def painting(page):
    return page.shape_kind.currentData() == "pixels"


def _anchor(page):
    """The target's pixel the offsets count from, fixed at the first paint; None without a target."""
    if page.paint_anchor is None and page.target is not None:
        page.paint_anchor = (round(page.target[0]), round(page.target[1]))
    return page.paint_anchor


def paint_click(page, x, y):
    a = _anchor(page)
    if a is None:
        page.result.setText(translate("PhotometryPaint", "Mark the target first."))
        return
    page.paint_pixels ^= {(round(x) - a[0], round(y) - a[1])}
    draw(page)


def paint_rect(page, x0, y0, x1, y1):
    a = _anchor(page)
    if not painting(page) or a is None:
        return
    xs, ys = sorted((round(x0), round(x1))), sorted((round(y0), round(y1)))
    page.paint_pixels |= {(x - a[0], y - a[1]) for x in range(xs[0], xs[1] + 1) for y in range(ys[0], ys[1] + 1)}
    draw(page)


def clear(page):
    page.paint_pixels = set()
    draw(page)


def from_threshold(page):
    from ..calibration.masters import load
    from ..photometry.pixels import threshold_mask

    a = _anchor(page)
    if not page.images or a is None:
        page.result.setText(translate("PhotometryPaint", "Choose the images and mark the target first."))
        return
    data = load(page.images[page.ref or 0])[0]
    mask = threshold_mask(data[None], reference=(a[1], a[0]))
    ys, xs = np.nonzero(mask)
    page.paint_pixels = {(int(x) - a[0], int(y) - a[1]) for x, y in zip(xs, ys, strict=True)}
    draw(page)


def draw(page):
    a = page.paint_anchor
    boxes = (
        [
            Box(x0=a[0] + dx - 0.5, y0=a[1] + dy - 0.5, x1=a[0] + dx + 0.5, y1=a[1] + dy + 0.5)
            for dx, dy in page.paint_pixels
        ]
        if a
        else []
    )
    page.viewer.set_items("paint", boxes)


def paint_shape(page):
    """{"kind": "pixels", "offsets": the painted pixels as offsets from each star's own pixel}."""
    if page.viewer.data is None or page.paint_anchor is None or not page.paint_pixels:
        return None
    return {"kind": "pixels", "offsets": [[int(dx), int(dy)] for dx, dy in page.paint_pixels]}

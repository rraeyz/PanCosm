"""The navigator (ARC-7 item 6): a thumbnail of the whole frame in the view's lower left corner with the part now
shown outlined; a click or drag in it moves the view. Drawn in the frame's own orientation (not turned)."""

import numpy as np

SIDE, MARGIN = 140, 12


def thumbnail(viewer):
    """The frame as a small QImage with the current levels, rebuilt only when the data or levels change."""
    from PySide6.QtGui import QImage

    from ...display import display_limits, to_display

    key = (id(viewer.data), viewer.interval, viewer.stretch, viewer.limits, viewer.invert)
    if getattr(viewer, "_nav_key", None) != key:
        h, w = viewer.data.shape[:2]
        step = max(1, int(np.ceil(max(h, w) / SIDE)))
        small = viewer.data[::step, ::step]
        limits = viewer.limits or display_limits(viewer.data, viewer.interval)
        pic = to_display(small, viewer.interval, viewer.stretch, limits)
        pic = np.ascontiguousarray(np.flipud(255 - pic if viewer.invert else pic))  # FITS row 0 is at the bottom
        n_h, n_w = pic.shape
        viewer._nav_image = QImage(pic.data, n_w, n_h, n_w, QImage.Format_Grayscale8).copy()
        viewer._nav_key = key
    return viewer._nav_image


def rect(viewer):
    """Where the thumbnail sits in viewport pixels."""
    from PySide6.QtCore import QRectF

    h, w = viewer.data.shape[:2]
    k = SIDE / max(h, w)
    return QRectF(MARGIN, viewer.viewport().height() - MARGIN - h * k, w * k, h * k)


def hit(viewer, pos):
    """Whether a viewport position is on the thumbnail (the view then goes there instead of panning)."""
    return viewer.data is not None and viewer.show_navigator and rect(viewer).contains(pos)


def go_to(viewer, pos):
    """Centre the view on the frame point under a thumbnail position."""
    from PySide6.QtCore import QPointF

    box, (h, w) = rect(viewer), viewer.data.shape[:2]
    viewer._fit_mode = False
    viewer.centerOn(QPointF((pos.x() - box.x()) / box.width() * w, (pos.y() - box.y()) / box.height() * h))


def draw(painter, viewer):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPen

    from ..kit import tokens

    box, w = rect(viewer), viewer.data.shape[1]
    painter.drawImage(box, thumbnail(viewer))
    painter.setPen(QPen(QColor(tokens.DARK["attention"]), 1))
    painter.setBrush(Qt.NoBrush)
    painter.drawRect(box)
    seen = viewer.mapToScene(viewer.viewport().rect()).boundingRect().intersected(viewer.sceneRect())
    k = box.width() / w
    painter.drawRect(
        box.x() + seen.x() * k, box.y() + seen.y() * k, max(seen.width() * k, 2), max(seen.height() * k, 2)
    )

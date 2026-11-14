"""The magnifier (ARC-7 item 6): the pixels around the cursor, 15 × 15 at 9× in a corner of the view, with the
current display levels, so a star's core and a hot pixel can be told apart without zooming."""

import numpy as np

HALF, SCALE, MARGIN = 7, 9, 12


def patch(data, row, col):
    """The (2·HALF+1)² pixels around (row, col), NaN beyond the frame edges; row 0 at the bottom (FITS)."""
    n = 2 * HALF + 1
    out = np.full((n, n), np.nan, np.float32)
    h, w = data.shape[:2]
    r0, c0 = row - HALF, col - HALF
    rs, re_ = max(r0, 0), min(r0 + n, h)
    cs, ce = max(c0, 0), min(c0 + n, w)
    if rs < re_ and cs < ce:
        out[rs - r0 : re_ - r0, cs - c0 : ce - c0] = data[rs:re_, cs:ce]
    return out


def draw(painter, viewer):
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QImage, QPen

    from ...display import display_limits, to_display
    from ..kit import tokens

    row, col = viewer.cursor_pixel
    if viewer._magnifier_limits is None:  # the frame's levels, once per image (or the levels the user set)
        viewer._magnifier_limits = display_limits(viewer.data, viewer.interval)
    limits = viewer.limits or viewer._magnifier_limits
    pic = np.ascontiguousarray(
        np.flipud(to_display(patch(viewer.data, row, col), viewer.interval, viewer.stretch, limits))
    )
    if viewer.invert:
        pic = 255 - pic
    n = pic.shape[0]
    image = QImage(pic.data, n, n, n, QImage.Format_Grayscale8).copy()
    side = n * SCALE
    target = QRectF(viewer.viewport().width() - side - MARGIN, MARGIN, side, side)
    painter.drawImage(target, image)
    painter.setPen(QPen(QColor(tokens.DARK["attention"]), 1))
    painter.setBrush(Qt.NoBrush)
    painter.drawRect(target)
    painter.drawRect(QRectF(target.x() + HALF * SCALE, target.y() + HALF * SCALE, SCALE, SCALE))  # the cursor's pixel


PRINT_ABOVE = 40  # screen pixels per image pixel from which the values are printed on the pixels themselves


def print_values(painter, viewer):
    """Each visible pixel's value written on it when the view is zoomed in past PRINT_ABOVE screen pixels."""
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor

    t = viewer.transform()
    zoom = abs(t.m11() * t.m22() - t.m12() * t.m21()) ** 0.5
    if zoom < PRINT_ABOVE:
        return
    h, w = viewer.data.shape[:2]
    seen = viewer.mapToScene(viewer.viewport().rect()).boundingRect()
    painter.setPen(QColor("#ffffff"))
    for r in range(max(int(seen.top()), 0), min(int(seen.bottom()) + 1, h)):
        for c in range(max(int(seen.left()), 0), min(int(seen.right()) + 1, w)):
            cell = viewer.mapFromScene(QRectF(c, r, 1, 1)).boundingRect()
            painter.drawText(cell, int(Qt.AlignCenter), f"{viewer.data[h - 1 - r, c]:.6g}")

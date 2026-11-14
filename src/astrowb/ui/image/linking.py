"""Linked views (ARC-7 item 8): panning and zooming one viewer moves the others, by pixel (same pixel under the
centre, same zoom) or by WCS (same sky position, same sky scale), for compare, RGB, before / after."""


def _zoom(view):
    t = view.transform()
    return abs(t.m11() * t.m22() - t.m12() * t.m21()) ** 0.5 or 1.0


def _follow(src, dst, by):
    from PySide6.QtCore import QPointF

    c = src.mapToScene(src.viewport().rect().center())
    zoom = _zoom(src)
    if by == "wcs" and src.wcs is not None and dst.wcs is not None:
        from . import orient

        x, y = c.x() - 0.5, src.data.shape[0] - 0.5 - c.y()
        x, y = dst.wcs.world_to_pixel(src.wcs.pixel_to_world(x, y))
        c = QPointF(float(x) + 0.5, dst.data.shape[0] - 0.5 - float(y))
        zoom *= orient.directions(src.wcs, src.data.shape)[2] / orient.directions(dst.wcs, dst.data.shape)[2]
    dst._fit_mode = False
    dst.resetTransform()
    dst.scale(zoom, zoom)
    dst.centerOn(c)


def link(a, b, by="pixel"):
    """Lock a and b both ways; by "wcs" falls back to pixels for a frame without a WCS. Returns a function that
    unlinks them."""
    busy = []

    def make(src, dst):
        def on_change():
            if busy or src.data is None or dst.data is None:
                return
            busy.append(1)
            try:
                _follow(src, dst, by)
            finally:
                busy.pop()

        return on_change

    ab, ba = make(a, b), make(b, a)
    a.view_changed.connect(ab)
    b.view_changed.connect(ba)
    ab()

    def unlink():
        a.view_changed.disconnect(ab)
        b.view_changed.disconnect(ba)

    return unlink

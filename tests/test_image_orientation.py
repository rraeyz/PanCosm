"""ARC-7 item 2: North up / East left from the WCS, flips and turns of the display only, compass and scale bar."""

import numpy as np
import pytest
from astropy.wcs import WCS
from PySide6.QtCore import QPointF

from astrowb.ui.image import orient


def sky(angle_deg, mirrored=False, scale_arcsec=1.5):
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [150.0, 30.0]
    w.wcs.crpix = [100, 80]
    a = np.radians(angle_deg)
    s = scale_arcsec / 3600
    w.wcs.cd = np.array([[-s * np.cos(a), s * np.sin(a)], [s * np.sin(a), s * np.cos(a)]])
    if mirrored:
        w.wcs.cd[:, 0] *= -1
    return w


@pytest.mark.parametrize("angle", [0, 30, 135, -70])
@pytest.mark.parametrize("mirrored", [False, True])
def test_north_up_east_left_on_screen(qapp, angle, mirrored):
    from astrowb.ui.viewer import ImageViewer

    v = ImageViewer()
    v.resize(500, 400)
    data = np.zeros((160, 200), np.float32)
    v.set_image(data, wcs=sky(angle, mirrored))
    assert v.north_up()
    north, east, scale = orient.directions(v.wcs, data.shape)
    assert scale == pytest.approx(1.5, rel=1e-3)
    centre = QPointF(100, 80)
    for vec, want in ((north, (0, -1)), (east, (-1, 0))):
        d = v.mapFromScene(centre + QPointF(*vec) * 40) - v.mapFromScene(centre)
        d = np.array([d.x(), d.y()]) / np.hypot(d.x(), d.y())
        assert d == pytest.approx(want, abs=0.05)
    v.grab()  # compass and scale bar draw without error
    v.close()


def test_scale_bar_lengths_are_round():
    assert orient.scale_bar(1.0) == (120, "2′")
    assert orient.scale_bar(0.5) == (120, "1′")
    assert orient.scale_bar(0.05) == (100, '5"')
    assert orient.scale_bar(30) == (120, "1°")


def test_flip_keeps_the_zoom(qapp):
    from astrowb.ui.viewer import ImageViewer

    v = ImageViewer()
    v.set_image(np.zeros((50, 50), np.float32))
    v.zoom(3)
    before = abs(v.transform().determinant())
    v.set_orientation(90, flip_x=True)
    assert abs(v.transform().determinant()) == pytest.approx(before)
    assert v.wcs is None and not v.north_up()
    v.close()

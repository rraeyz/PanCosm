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


def test_overlay_layers_hide_and_show(qapp):
    from PySide6.QtWidgets import QMenu

    from astrowb.ui.overlay_actions import _fill_layers
    from astrowb.ui.viewer import ImageViewer

    v = ImageViewer()
    v.set_image(np.zeros((50, 50), np.float32))
    v.set_overlay("grid", lines=[[(0, 0), (10, 10)]])
    v.set_overlay("gaia", circles=[(5, 5, 3, "a")])
    menu = QMenu()
    _fill_layers(v, menu)
    acts = {a.text(): a for a in menu.actions()}
    assert set(acts) == {"gaia", "grid"} and all(a.isChecked() for a in acts.values())
    acts["grid"].setChecked(False)
    assert not v.layer_visible("grid") and v.layer_visible("gaia")
    v.set_layer("gaia", opacity=0.3)
    assert v._overlays["gaia"][0].opacity() == pytest.approx(0.3)
    v.close()


def test_magnifier_shows_the_pixels_round_the_cursor(qapp):
    from astrowb.ui.image import magnifier
    from astrowb.ui.viewer import ImageViewer

    data = np.zeros((40, 50), np.float32)
    data[0, 0] = 9.0
    p = magnifier.patch(data, 0, 0)  # at the corner: what lies beyond the frame is empty
    assert p.shape == (15, 15) and p[7, 7] == 9.0 and np.isnan(p[0, 0]) and p[7, 8] == 0.0
    v = ImageViewer()
    v.resize(400, 300)
    v.set_image(data)
    v.show_magnifier, v.cursor_pixel = True, (20, 25)
    v.grab()  # draws without error
    assert v._magnifier_limits is not None
    v.close()


def test_imexamine_keys_over_the_image(qapp):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    from astrowb.ui.viewer import ImageViewer

    v = ImageViewer()
    v.set_image(np.zeros((40, 60), np.float32))
    got = []
    v.star_key.connect(lambda x, y: got.append(("a", x, y)))
    v.region_selected.connect(lambda *r: got.append(("m", *r)))
    v.line_selected.connect(lambda *r: got.append(("line", *r)))
    v.cursor_pixel = (10, 20)  # row 10, column 20
    for key in (Qt.Key_A, Qt.Key_M, Qt.Key_L, Qt.Key_C):
        QTest.keyClick(v, key)
    assert got == [("a", 20, 10), ("m", 15, 5, 25, 15), ("line", 0, 10, 59, 10), ("line", 20, 0, 20, 39)]
    QTest.keyClick(v, Qt.Key_M, Qt.ControlModifier)  # with a modifier: not an examine key
    assert len(got) == 4
    v.close()


def test_zoom_keys_over_the_image(qtbot):
    """UI-12: + / − zoom, 1 shows image pixels 1:1, 0 fits the image again."""
    import numpy as np
    from PySide6.QtCore import Qt

    from astrowb.ui.viewer import ImageViewer

    v = ImageViewer()
    qtbot.addWidget(v)
    v.resize(300, 300)
    v.show()
    v.set_image(np.random.default_rng(1).normal(100, 5, (600, 600)).astype(np.float32))
    fitted = v.transform().m11()
    assert fitted < 1  # 600 px fitted into 300
    qtbot.keyClicks(v, "+")
    assert v.transform().m11() > fitted
    qtbot.keyClick(v, Qt.Key_1)
    assert v.transform().m11() == 1.0
    qtbot.keyClick(v, Qt.Key_Minus)
    assert v.transform().m11() == 0.8
    qtbot.keyClick(v, Qt.Key_0)
    assert abs(v.transform().m11() - fitted) < 1e-9 and v._fit_mode


def test_bracket_keys_step_the_frames(qtbot):
    """UI-12: [ and ] over an image ask for the previous / next frame of the series."""
    import numpy as np

    from astrowb.ui.viewer import ImageViewer

    v = ImageViewer()
    qtbot.addWidget(v)
    v.set_image(np.zeros((10, 10), np.float32))
    steps = []
    v.step_frame.connect(steps.append)
    qtbot.keyClicks(v, "][")
    assert steps == [1, -1]


def test_invert_key_keeps_the_levels(qtbot):
    """UI-12: i inverts the display and keeps the black and white levels chosen."""
    import numpy as np

    from astrowb.ui.viewer import ImageViewer

    v = ImageViewer()
    qtbot.addWidget(v)
    v.set_image(np.arange(100, dtype=np.float32).reshape(10, 10))
    v.set_levels((10.0, 50.0))
    qtbot.keyClicks(v, "i")
    assert v.invert and v.limits == (10.0, 50.0)
    qtbot.keyClicks(v, "n")  # no WCS: North up does nothing, without an error
    assert not v.north_up()

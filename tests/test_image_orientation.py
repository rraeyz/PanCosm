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
    blinks = []
    v.blink_key.connect(lambda: blinks.append(1))
    qtbot.keyClicks(v, "][b")
    assert steps == [1, -1] and blinks == [1]


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


def test_layer_specs_become_items(qapp):
    from astrowb.ui.image import layers as L
    from astrowb.ui.viewer import ImageViewer

    v = ImageViewer()
    v.resize(300, 200)
    v.set_image(np.zeros((40, 50), np.float32))
    v.set_items(
        "marks",
        [
            L.Circle(x=10, y=10, r=4, label="c", id="s1", pickable=True),
            L.Annulus(x=10, y=10, r_in=5, r_out=8),
            L.Ellipse(x=20, y=20, a=6, b=3, angle=30),
            L.Box(x0=1, y0=1, x1=9, y1=5),
            L.Polyline(points=((0, 0), (5, 5), (9, 2))),
            L.Text(x=3, y=3, text="t"),
            L.Cross(x=30, y=30, fixed=True),
        ],
    )
    items = v._overlays["marks"]
    assert len(items) == 7 and items[0].data(1) == "s1" and items[0].data(2) is True
    assert items[0].toolTip() == "c" and items[0].pos().x() == 10.5 and items[0].pos().y() == 29.5
    assert not items[0].flags() & items[0].GraphicsItemFlag.ItemIgnoresTransformations
    assert items[6].flags() & items[6].GraphicsItemFlag.ItemIgnoresTransformations  # fixed screen size
    v.set_layer("marks", visible=False)
    assert not v.layer_visible("marks")
    v.set_items("marks", [])
    assert v.overlay_names() == []
    v.close()


def test_navigator_moves_the_view_and_values_print(qapp):
    from PySide6.QtCore import QPointF

    from astrowb.ui.image import navigator
    from astrowb.ui.viewer import ImageViewer

    v = ImageViewer()
    v.resize(400, 300)
    v.show_navigator = True
    data = np.arange(200 * 100, dtype=np.float32).reshape(100, 200)
    v.set_image(data)
    v.zoom(8)
    box = navigator.rect(v)
    assert navigator.hit(v, box.center()) and not navigator.hit(v, QPointF(390, 5))
    navigator.go_to(v, QPointF(box.x() + 0.25 * box.width(), box.y() + 0.5 * box.height()))
    centre = v.mapToScene(v.viewport().rect().center())
    assert abs(centre.x() - 50) < 1 and abs(centre.y() - 50) < 1
    v.grab()  # thumbnail and rectangle draw
    v.resetTransform()
    v.scale(45, 45)  # past 40 screen pixels per pixel: the values are printed
    v.grab()
    v.close()


def _wcs(scale=1.0, crval=(150.0, 20.0)):
    from astropy.wcs import WCS

    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval, w.wcs.crpix, w.wcs.cdelt = crval, (50, 40), (-scale / 3600, scale / 3600)
    return w


def test_readout_degrees_match_astropy():
    from astrowb.ui.image.readout import sky_text

    w = _wcs()
    text = sky_text(w, 49, 39)  # the reference pixel (0-based)
    assert "150.00000°" in text and "+20.00000°" in text and "10h00m00.0s" in text


def test_linked_views_follow_by_pixel_and_by_wcs(qapp):
    from astrowb.ui.image.linking import link
    from astrowb.ui.viewer import ImageViewer

    a, b = ImageViewer(), ImageViewer()
    for v in (a, b):
        v.resize(300, 200)
    a.set_image(np.zeros((80, 100), np.float32), wcs=_wcs(1.0))
    b.set_image(np.zeros((80, 100), np.float32), wcs=_wcs(2.0))  # twice the pixel scale: half the zoom
    unlink = link(a, b, "pixel")
    a.zoom(4)
    za, zb = a.transform().m11(), b.transform().m11()
    assert abs(za - zb) < 1e-9
    unlink()
    a.zoom(2)
    assert abs(b.transform().m11() - zb) < 1e-9
    unlink = link(a, b, "wcs")
    assert abs(b.transform().m11() / (a.transform().m11() / 2) - 1) < 1e-6
    ca, cb = a.mapToScene(a.viewport().rect().center()), b.mapToScene(b.viewport().rect().center())
    assert abs(ca.x() - cb.x()) < 1 and abs(ca.y() - cb.y()) < 1  # same sky centre, same pixel grid here
    unlink()
    a.close()
    b.close()


def test_sequence_steps_plays_and_fixes_levels(qapp):
    from astrowb.ui.image.sequence import SequenceBar
    from astrowb.ui.viewer import ImageViewer

    loaded = []

    def loader(path):
        loaded.append(path)
        return np.full((30, 40), float(path), np.float32) + np.arange(40, dtype=np.float32), None

    v = ImageViewer()
    bar = SequenceBar(v, [1, 2, 3], loader)
    assert bar.index == 0 and v.data[0, 0] == 1.0
    bar.same_levels.setChecked(True)
    fixed = v.limits
    bar.step(1)
    assert bar.index == 1 and v.data[0, 0] == 2.0 and v.limits == fixed
    bar.step(1)
    bar.step(1, wrap=True)  # play wraps round to the first frame
    assert bar.index == 0
    bar.same_levels.setChecked(False)
    assert v.limits is None
    assert 2 in loaded and 3 in loaded  # the neighbours were read ahead
    bar.frames.close()
    v.close()

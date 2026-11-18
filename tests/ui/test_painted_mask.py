import json

import numpy as np
import pytest

from astrowb.photometry.aperture import measure
from astrowb.ui import photometry_paint as paint
from astrowb.ui.photometry_page import PhotometryPage


def _frame(size=61):
    yy, xx = np.mgrid[:size, :size]
    noise = np.random.default_rng(1).normal(0, 3.0, (size, size))
    return 100.0 + noise + 5000 * np.exp(-((xx - 30) ** 2 + (yy - 30) ** 2) / (2 * 2.0**2))


def _page(qtbot, monkeypatch):
    page = PhotometryPage()
    qtbot.addWidget(page)
    page.images, page.target = ["f.fits"], (30.0, 30.0)
    img = _frame()
    page.viewer.data = img
    monkeypatch.setattr("astrowb.calibration.masters.load", lambda p: (img, {}))
    page.shape_kind.setCurrentIndex(page.shape_kind.findData("pixels"))
    return page, img


def test_clicks_toggle_pixels_and_clear(qtbot, monkeypatch):
    page, _ = _page(qtbot, monkeypatch)
    page._clicked(30.2, 29.8)
    page._clicked(31.0, 30.0)
    assert page.paint_pixels == {(0, 0), (1, 0)}
    assert len(page.viewer._overlays["paint"]) == 2
    page._clicked(30.0, 30.0)  # a second click takes it off
    assert page.paint_pixels == {(1, 0)}
    page.paint_clear.click()
    assert not page.paint_pixels and "paint" not in page.viewer._overlays


def test_rectangle_and_shape_passed_to_the_engine(qtbot, monkeypatch):
    page, img = _page(qtbot, monkeypatch)
    page.comps = [(10.0, 10.0)]
    paint.paint_rect(page, 28, 28, 32, 32)
    s = paint.paint_shape(page)
    assert s["kind"] == "pixels" and len(s["offsets"]) == 25  # each star gets the same pixels around itself
    m = np.zeros(img.shape, bool)
    m[28:33, 28:33] = True
    flux = measure(img, [(30.0, 30.0), (10.0, 10.0)], 6, 14, 20, shape=s)[0]
    assert flux[0] == pytest.approx((img[m] - 100.0).sum(), rel=1e-2)
    assert json.dumps(s)  # small and JSON: the project log stores step parameters


def test_from_threshold_paints_the_star(qtbot, monkeypatch):
    page, _ = _page(qtbot, monkeypatch)
    page.paint_threshold.click()
    assert (0, 0) in page.paint_pixels and 5 < len(page.paint_pixels) < 400

import numpy as np

from astrowb.photometry import aperture
from astrowb.photometry.measurements import measurements
from astrowb.ui.photometry_page import PhotometryPage


def _star(angle=35.0, ratio=0.5, size=61):
    yy, xx = np.mgrid[:size, :size] - size // 2
    t = np.radians(angle)
    u, v = xx * np.cos(t) + yy * np.sin(t), -xx * np.sin(t) + yy * np.cos(t)
    return 100.0 + 5000 * np.exp(-(u**2 / (2 * 3.0**2) + v**2 / (2 * (3.0 * ratio) ** 2)))


def _page(qtbot, monkeypatch):
    page = PhotometryPage()
    qtbot.addWidget(page)
    page.images, page.target = ["f.fits"], (30.0, 30.0)
    monkeypatch.setattr("astrowb.calibration.masters.load", lambda p: (_star(), {}))
    return page


def test_circle_is_the_default(qtbot, monkeypatch):
    from astrowb.ui.photometry_shape import shape_params, shape_text

    page = _page(qtbot, monkeypatch)
    assert shape_params(page) is None and shape_text(page) == "circle"


def test_read_from_the_star(qtbot, monkeypatch):
    from astrowb.ui.photometry_shape import shape_params, shape_text

    page = _page(qtbot, monkeypatch)
    page.r_ap.setValue(10.0)
    page.shape_kind.setCurrentIndex(1)
    page.shape_read.click()
    s = shape_params(page)
    assert s["kind"] == "ellipse" and s["ratio"] < 0.8
    assert abs(s["angle"] - 35.0) < 8
    assert shape_text(page).startswith("ellipse")
    assert page.star_table.item(0, 6).text() == shape_text(page)


def test_ellipse_measurement_and_columns(qtbot):
    data = _star()
    shape = {"kind": "ellipse", "ratio": 0.5, "angle": 35.0}
    flux = aperture.measure(data, [(30, 30)], 9.0, 14.0, 20.0, shape=shape)[0]
    assert np.isfinite(flux).all() and flux[0] > 0
    lc = {"file": ["a"], "target_flux": [1.0], "rel_flux": [1.0], "rel_flux_err": [0.1], "radii": [[9.0, 14.0, 20.0]],
          "shape": shape}  # fmt: skip
    cols, _ = measurements(lc)
    assert cols["Ap_shape"] == ["ellipse"] and cols["Ap_a"] == [9.0]
    assert cols["Ap_b"] == [4.5] and cols["Ap_angle"] == [35.0]
    lc.pop("shape")
    cols, _ = measurements(lc)
    assert cols["Ap_shape"] == ["circle"] and cols["Ap_b"] == [9.0]

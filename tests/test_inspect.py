"""Image-information tools: counts in a rectangle, along a line, in a star's aperture; known answers."""

import numpy as np
import pytest
from test_apertures import field

from astrowb.io import inspect


def test_area_counts_on_a_known_array():
    a = np.arange(100.0).reshape(10, 10)  # value = 10 * row + column
    s = inspect.area_stats(a, 4, 5, 2, 3, gain=2.0)  # corners in any order
    assert (s["x0"], s["y0"], s["x1"], s["y1"], s["pixels"]) == (2, 3, 4, 5, 9)
    assert s["sum"] == 387.0 and s["mean"] == 43.0 and s["median"] == 43.0 and s["sum_electrons"] == 774.0
    assert s["min"] == 32.0 and s["min_xy"] == (2, 3) and s["max"] == 54.0 and s["max_xy"] == (4, 5)
    assert s["std"] == pytest.approx(np.std([32, 33, 34, 42, 43, 44, 52, 53, 54], ddof=1))
    assert inspect.area_stats(a, -5, -5, 1, 1)["pixels"] == 4  # clipped to the image
    with pytest.raises(ValueError):
        inspect.area_stats(a, 20, 20, 30, 30)


def test_line_and_box_profiles():
    a = np.tile(np.arange(50.0), (40, 1))  # value = x
    p = inspect.line_profile(a, 5, 10, 25, 10)
    assert p["length"] == 20 and p["angle"] == 0 and len(p["values"]) == 21
    assert p["values"] == pytest.approx(np.arange(5, 26))
    v = inspect.line_profile(a, 7.5, 0, 7.5, 30)
    assert v["angle"] == 90 and np.allclose(v["values"], 7.5)  # between two columns: interpolated
    b = np.add.outer(np.arange(40.0), np.zeros(50))  # value = y
    wide = inspect.line_profile(b, 0, 20, 40, 20, width=5)  # averages y = 18..22
    assert np.allclose(wide["values"], 20)
    assert inspect.box_profile(a, 3, 2, 6, 9, axis="x")["values"] == [3, 4, 5, 6]
    assert inspect.box_profile(b, 3, 2, 6, 4, axis="y")["values"] == [2, 3, 4]
    h = inspect.histogram(np.arange(1000.0), bins=10)
    assert sum(h["counts"]) == 1000 and h["counts"][0] == 100


def test_star_measurements_match_the_simulation():
    img = field(4.0, stars=[(100.3, 90.6, 2e5)], seed=3)
    s = inspect.star_info(img, 101, 91, gain=1.0, exptime=10.0)
    assert (s["x"], s["y"]) == pytest.approx((100.3, 90.6), abs=0.05)
    assert s["fwhm"] == pytest.approx(4.0, rel=0.05)
    assert s["hfd"] == pytest.approx(4.0, rel=0.1)  # Gaussian: half the light within FWHM / 2
    assert s["background"] == pytest.approx(300, abs=3)
    ee = 1 - np.exp(-(s["r_ap"] ** 2) / (2 * (4.0 / 2.3548) ** 2))  # Gaussian light inside the aperture
    assert s["net_counts"] == pytest.approx(2e5 * ee, rel=0.01)
    assert s["snr"] == pytest.approx(s["net_counts"] / s["net_counts_err"])
    assert s["instrumental_mag"] == pytest.approx(-2.5 * np.log10(s["net_counts"] / 10.0))
    assert s["ellipticity"] < 0.05 and not s["saturated"]
    assert inspect.star_info(img, 101, 91, saturation=5000.0)["saturated"]
    fixed = inspect.star_info(img, 101, 91, r_ap=6.0)
    assert (fixed["r_ap"], fixed["r_in"]) == (6.0, 18.0)


def test_elongated_star_has_its_ellipticity_and_angle():
    yy, xx = np.mgrid[:120, :120]
    img = 100 + 5e4 / (2 * np.pi * 3 * 1.5) * np.exp(-((xx - 60) ** 2) / (2 * 3.0**2) - (yy - 60) ** 2 / (2 * 1.5**2))
    s = inspect.star_info(img, 60, 60, r_ap=10.0, r_in=20.0, r_out=30.0)
    assert s["ellipticity"] == pytest.approx(0.5, abs=0.03)
    assert abs(s["position_angle"]) < 2  # long axis along x


def test_saturation_level_from_header():
    from astropy.io import fits

    assert inspect.saturation_level(fits.Header({"SATURATE": 60000})) == 60000
    assert inspect.saturation_level(fits.Header(), np.array([[10.0, 30000.0]])) == 65535
    assert inspect.saturation_level(fits.Header(), np.array([[0.1, 2.0]])) is None


def test_images_page_tools(qtbot, tmp_path):
    from astropy.io import fits

    from astrowb.ui.workspaces import ImagePage

    page = ImagePage()
    qtbot.addWidget(page)
    img = field(4.0)
    page.viewer.set_image(img)
    page.set_header(fits.Header({"EXPTIME": 10.0, "GAIN": 2.0}))
    page.set_tool("aperture")
    assert page.viewer.tool == "aperture"
    page.viewer.clicked.emit(60.0, 71.0)
    names = [page.info.item(i, 0).text() for i in range(page.info.rowCount())]
    assert "Net counts in the aperture" in names and "Net electrons" in names and "FWHM (px)" in names
    assert page.graph is not None and page.graph.figure.axes
    page.set_tool("area")
    page.viewer.region_selected.emit(10.0, 10.0, 29.0, 19.0)
    values = {page.info.item(i, 0).text(): page.info.item(i, 1).text() for i in range(page.info.rowCount())}
    assert values["Pixels"] == "200" and values["Size (px)"] == "20 × 10"
    for i in range(page.graph_kind.count()):  # histogram, row and column profiles, 3-D surface
        page.graph_kind.setCurrentIndex(i)
        assert page.graph.figure.axes
    page.graph_kind.setCurrentIndex(1)
    out = page.export_graph(tmp_path / "row.csv")
    assert (tmp_path / "row.csv").read_text(encoding="utf-8").splitlines()[0].startswith("x (FITS pixels)") and out
    page.set_tool("line")
    page.viewer.line_selected.emit(0.0, 70.6, 199.0, 70.6)
    values = {page.info.item(i, 0).text(): page.info.item(i, 1).text() for i in range(page.info.rowCount())}
    assert values["Length (px)"] == "199.00"
    assert page.measure_whole()["pixels"] == 200 * 200

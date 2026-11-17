"""UI-16.13: grid, scale bar and north arrow of the Remote sensing map, from the scene's georeference."""

import math

import numpy as np
import pytest

from astrowb.remotesensing.raster import Raster
from astrowb.ui import rs_map_layers as ml


def geo(transform, epsg, ny=100, nx=100):
    return Raster(np.zeros((1, ny, nx), np.float32), ["B1"], transform, epsg)


def test_grid_lines_sit_at_round_longitudes_and_latitudes():
    r = geo((10.0, 0.01, 0, 50.0, 0, -0.01), 4326)  # 1 degree square, 0.01 deg per pixel
    lines = ml.grid_lines(r, 0, 0, 100, 100)
    assert {k for (k, _), _ in lines} == {"lon", "lat"}
    for (kind, v), pts in lines:
        assert v * 6 == pytest.approx(round(v * 6))  # a multiple of 10 arc-minutes
        for col, row in pts:
            lon, lat = r.lonlat(col, row)
            assert (lon if kind == "lon" else lat) == pytest.approx(v, abs=1e-6)
    lons = [round(v, 6) for (k, v), _ in lines if k == "lon"]
    assert any(v == pytest.approx(10 + 1 / 6) for v in lons)


def test_scale_bar_length_is_metres_over_pixel_size():
    r = geo((500000.0, 30.0, 0, 4100000.0, 0, -30.0), 32635)
    assert ml.pixel_size_m(r) == pytest.approx(30.0)
    assert ml.nice_length(0.25 * 100 * 30) == 500  # a quarter of the width, rounded down to 1-2-5
    assert 500 / ml.pixel_size_m(r) == pytest.approx(500 / 30)  # the bar's length in picture pixels
    assert ml.pixel_size_m(geo((10.0, 0.01, 0, 50.0, 0, -0.01), 4326)) is None  # degrees: no metres
    assert ml.pixel_size_m(geo(None, None)) is None


def test_north_arrow_follows_a_rotated_transform():
    up = geo((500000.0, 30.0, 0, 4100000.0, 0, -30.0), 32635)
    dx, dy = ml.north_direction(up)
    assert dx == pytest.approx(0, abs=0.01) and dy == pytest.approx(-1, abs=0.01)  # north is up the picture
    t = math.radians(30)
    a, b = 30 * math.cos(t), 30 * math.sin(t)
    rot = geo((500000.0, a, b, 4100000.0, b, -a), 32635)
    dx, dy = ml.north_direction(rot)
    assert abs(math.degrees(math.atan2(dx, -dy))) == pytest.approx(30, abs=1.0)  # leans 30 degrees from up


def test_layers_are_disabled_with_a_reason_without_a_georeference(qtbot):
    from astrowb.ui.rs_layers import install
    from astrowb.ui.rs_page import RemoteSensingPage

    page = RemoteSensingPage()
    qtbot.addWidget(page)
    install(page)
    page.raster = geo(None, None)
    page.map_layers.refresh()
    for box in page.map_layers.boxes.values():
        assert not box.isEnabled() and box.toolTip()
    page.raster = geo((500000.0, 30.0, 0, 4100000.0, 0, -30.0), 32635)
    page.map_layers.refresh()
    assert all(b.isEnabled() for b in page.map_layers.boxes.values())
    page.show()
    page.viewer.resize(300, 300)
    page.viewer.set_image(np.zeros((100, 100), np.float32))
    for b in page.map_layers.boxes.values():
        b.setChecked(True)
    assert len(page.map_layers.items) > 4  # grid lines and labels, the bar and its label, the arrow and its N
    page.map_layers.boxes["Grid"].setChecked(False)
    assert len(page.map_layers.items) == 4

"""Remote sensing: GeoTIFF round trip with georeferencing, band math safety, indices, classes, PCA."""

import numpy as np
import pytest
import tifffile

from astrowb.remotesensing import analysis, raster

# a 4-band UTM zone 35N scene (EPSG 32635): 30 m pixels, upper-left corner at E 500000, N 4100000
SCALE = (33550, "d", 3, (30.0, 30.0, 0.0))
TIE = (33922, "d", 6, (0.0, 0.0, 0.0, 500000.0, 4100000.0, 0.0))
GEOKEYS = (34735, "H", 16, (1, 1, 0, 3, 1024, 0, 1, 1, 1025, 0, 1, 1, 3072, 0, 1, 32635))


def scene(tmp_path, ny=60, nx=80):
    rng = np.random.default_rng(1)
    water = np.zeros((ny, nx), bool)
    water[:, :20] = True
    veg = np.zeros((ny, nx), bool)
    veg[:, 50:] = True
    blue = np.where(water, 0.08, 0.06) + rng.normal(0, 0.003, (ny, nx))
    green = np.where(water, 0.10, np.where(veg, 0.09, 0.12)) + rng.normal(0, 0.003, (ny, nx))
    red = np.where(water, 0.05, np.where(veg, 0.04, 0.20)) + rng.normal(0, 0.003, (ny, nx))
    nir = np.where(water, 0.02, np.where(veg, 0.45, 0.25)) + rng.normal(0, 0.003, (ny, nx))
    data = np.stack([blue, green, red, nir]).astype(np.float32)
    path = tmp_path / "scene.tif"
    tifffile.imwrite(
        path,
        data,
        planarconfig="separate",
        photometric="minisblack",
        extratags=[(*SCALE, True), (*TIE, True), (*GEOKEYS, True)],
    )
    return path, water, veg


def test_geotiff_round_trip_keeps_georeferencing(tmp_path):
    path, _, _ = scene(tmp_path)
    r = raster.read(path)
    assert r.bands.shape == (4, 60, 80) and r.epsg == 32635
    assert r.map_xy(0, 0) == (500000.0, 4100000.0) and r.map_xy(10.5, 2.5) == (500315.0, 4099925.0)
    lon, lat = r.lonlat(40, 30)  # zone 35N central meridian is 27 E; 500 km easting is on it
    assert lon == pytest.approx(27.0, abs=0.02) and lat == pytest.approx(37.04, abs=0.05)
    out = raster.write(
        tmp_path / "ndvi.tif", r, analysis.evaluate("(B4 - B3) / (B4 + B3)", dict(zip(r.names, r.bands, strict=True)))
    )
    back = raster.read(out)
    assert back.epsg == 32635 and back.transform == r.transform and back.bands.shape == (1, 60, 80)


def test_band_math_is_safe_and_correct(tmp_path):
    b = {"B1": np.array([1.0, 2.0, 0.0]), "B2": np.array([3.0, 2.0, 0.0])}
    assert np.allclose(analysis.evaluate("(B2 - B1) / (B2 + B1)", b)[:2], [0.5, 0.0])
    assert np.isnan(analysis.evaluate("(B2 - B1) / (B2 + B1)", b)[2])  # 0/0 -> NaN, not inf or warning
    assert np.allclose(analysis.evaluate("where(B1 > 1, sqrt(B2), -B1)", b), [-1.0, np.sqrt(2), -0.0])
    for bad in ("__import__('os').system('true')", "B1.__class__", "open('x')", "[1, 2]", "B9 + 1", "B1 +"):
        with pytest.raises(analysis.ExpressionError):
            analysis.evaluate(bad, b)


def test_indices_classes_and_pca(tmp_path):
    path, water, veg = scene(tmp_path)
    r = raster.read(path)
    bands = dict(zip(r.names, r.bands, strict=True))
    roles = {"BLUE": "B1", "GREEN": "B2", "RED": "B3", "NIR": "B4"}
    ndvi = analysis.evaluate(analysis.index_expression("NDVI", roles), bands)
    ndwi = analysis.evaluate(analysis.index_expression("NDWI", roles), bands)
    assert np.median(ndvi[veg]) == pytest.approx((0.45 - 0.04) / 0.49, abs=0.01)
    assert np.all(ndwi[water] > 0.5) and np.all(ndwi[veg] < 0)
    labels = analysis.kmeans(r.bands, k=3)
    for region in (water, veg, ~(water | veg)):  # each surface type is one class
        vals, counts = np.unique(labels[region], return_counts=True)
        assert counts.max() / region.sum() > 0.99
    comps, var = analysis.pca(r.bands, 2)
    assert comps.shape == (2, 60, 80) and var[0] >= var[1] and 0.95 < sum(var) <= 1.0  # 3 surfaces: a plane
    st = analysis.statistics(ndvi)
    assert st["n"] == 4800 and st["min"] < 0 < st["max"]
    d, mask = analysis.change(ndvi, ndvi + np.where(veg, -0.5, 0.0).astype(np.float32), 0.2)
    assert mask[veg].all() and not mask[water].any()
    assert analysis.pixel_spectrum(r.bands, 70, 10) == pytest.approx([0.06, 0.09, 0.04, 0.45], abs=0.02)

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


def test_band_files_of_one_scene_open_as_one_image(tmp_path, qtbot):
    """Sentinel-2 comes as one file per band: B04 and B08 together give NDVI; roles without a band stay empty."""
    import tifffile

    from astrowb.remotesensing import analysis, raster
    from astrowb.ui.rs_page import RemoteSensingPage

    red, nir = np.full((40, 30), 1000, np.uint16), np.full((40, 30), 3000, np.uint16)
    for name, data in (("B04", red), ("B08", nir)):
        tifffile.imwrite(tmp_path / f"{name}.tif", data)
    both = f"{tmp_path / 'B04.tif'};{tmp_path / 'B08.tif'}"
    r = raster.read(both)
    assert r.names == ["B04", "B08"] and r.bands.shape == (2, 40, 30) and r.source == both
    page = RemoteSensingPage()
    qtbot.addWidget(page)
    page.open(both)
    roles = {k: c.currentText() for k, c in page.roles.items()}
    assert roles == {"BLUE": "", "GREEN": "", "RED": "B04", "NIR": "B08", "SWIR": ""}
    page._preset(page.index.findText("NDVI"))
    assert page.expression.text() == "(B08 - B04) / (B08 + B04)"
    assert analysis.evaluate(page.expression.text(), {"B04": r.band(0), "B08": r.band(1)})[0, 0] == pytest.approx(0.5)
    with pytest.raises(analysis.ExpressionError, match="unknown band GREEN"):  # NDWI needs a green band
        analysis.evaluate(analysis.index_expression("NDWI", {"RED": "B04", "NIR": "B08"}), {"B04": red, "B08": nir})
    big = analysis.evaluate("B08 / B04", {"B04": np.ones((3000, 4)), "B08": np.full((3000, 4), 2.0)}, rows=1000)
    assert big.shape == (3000, 4) and np.all(big == 2.0)  # in blocks of rows


def test_block_wise_pca_and_kmeans_give_what_a_copy_of_every_pixel_gave():
    """The classes and components are computed block by block (a copy of every valid pixel was 1 GB more on a
    Sentinel-2 tile): same sample, same centres, same classes and components as the copy-everything version."""
    from scipy.cluster.vq import kmeans2

    rng = np.random.default_rng(3)
    bands = rng.normal([[[1.0]], [[5.0]], [[-2.0]]], 1.0, (3, 300, 410)).astype(np.float32)
    bands[1, :40] += 4.0  # two kinds of surface
    bands[0, rng.random((300, 410)) < 0.03] = np.nan  # missing pixels in one band

    def pixels(b):  # the earlier version
        cube = np.asarray(b, np.float32)
        valid = np.all(np.isfinite(cube), axis=0)
        x = cube[:, valid]
        for row in x:
            row -= np.float32(row.mean(dtype=np.float64))
            row /= np.float32(row.std(dtype=np.float64))
        return x, valid

    x, valid = pixels(bands)
    pick = np.random.default_rng(0).choice(x.shape[1], 5000, replace=False)
    centres, _ = kmeans2(np.asarray(x[:, pick].T, np.float64), 4, minit="++", seed=0)
    centres = centres[np.argsort(centres[:, 0])].astype(np.float32)
    ref = np.full(valid.shape, np.nan, np.float32)
    ref[valid] = np.argmin(((x.T[:, None, :] - centres[None]) ** 2).sum(axis=2), axis=1)
    got = analysis.kmeans(bands, k=4, sample=5000)
    assert np.array_equal(np.isnan(got), np.isnan(ref)) and np.mean(got[valid] == ref[valid]) > 0.9999
    var, vec = np.linalg.eigh(np.cov(x[:, :: x.shape[1] // 20000].astype(np.float64)))
    order = np.argsort(var)[::-1]
    comps, explained = analysis.pca(bands, 2, sample=20000)
    assert explained == pytest.approx((var[order][:2] / var.sum()).tolist(), rel=1e-6)
    for i in range(2):
        v = vec[:, order[i]].astype(np.float32)
        expect = v @ x
        sign = np.sign(np.dot(comps[i][valid][:100], expect[:100]))  # an eigenvector's sign is arbitrary
        assert np.allclose(sign * comps[i][valid], expect, atol=1e-5) and np.isnan(comps[i][~valid]).all()


def test_esa_sentinel2_bands_become_reflectance_with_the_baseline_offset(tmp_path):
    """Band files of an ESA SAFE product carry +1000 since processing baseline 04.00: they are read as
    (number + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE from the product's MTD_MSIL2A.xml, so NDVI is right
    (on the raw numbers red 0.05 / NIR 0.30 gave 0.455 instead of 0.714); 0 is no data; a class map (SCL) and files
    outside a SAFE product are left as they are."""
    import imagecodecs

    from astrowb.remotesensing import raster

    safe = tmp_path / "S2B_MSIL2A_20250828T083559_N0511_R064_T36TVK_20250828T110000.SAFE"
    img = safe / "GRANULE" / "L2A_T36TVK" / "IMG_DATA" / "R10m"
    img.mkdir(parents=True)
    offsets = "".join(f'<BOA_ADD_OFFSET band_id="{i}">-1000</BOA_ADD_OFFSET>' for i in range(13))
    (safe / "MTD_MSIL2A.xml").write_text(
        '<?xml version="1.0"?><n1:Level-2A_User_Product xmlns:n1="https://psd-14.sentinel2.eo.esa.int/PSD/'
        'User_Product_Level-2A.xsd"><General_Info><Product_Image_Characteristics><QUANTIFICATION_VALUES_LIST>'
        '<BOA_QUANTIFICATION_VALUE unit="none">10000</BOA_QUANTIFICATION_VALUE></QUANTIFICATION_VALUES_LIST>'
        f"<BOA_ADD_OFFSET_VALUES_LIST>{offsets}</BOA_ADD_OFFSET_VALUES_LIST></Product_Image_Characteristics>"
        "</General_Info></n1:Level-2A_User_Product>"
    )
    red = np.full((20, 30), 1500, np.uint16)
    nir = np.full((20, 30), 4000, np.uint16)
    red[0, 0] = nir[0, 0] = 0
    paths = []
    for band, a in (("B04", red), ("B08", nir), ("SCL", red)):
        p = img / f"T36TVK_20250828T083559_{band}_10m.jp2"
        p.write_bytes(imagecodecs.jpeg2k_encode(a, level=0))
        paths.append(p)
    r, n = raster.read(paths[0]).bands[0], raster.read(paths[1]).bands[0]
    assert r[5, 5] == pytest.approx(0.05) and n[5, 5] == pytest.approx(0.30) and np.isnan(r[0, 0])
    assert ((n - r) / (n + r))[5, 5] == pytest.approx(0.25 / 0.35)
    assert raster.read(paths[2]).bands[0][5, 5] == 1500  # a class map keeps its classes
    outside = tmp_path / "T36TVK_20250828T083559_B04_10m.jp2"
    outside.write_bytes(paths[0].read_bytes())
    assert raster.read(outside).bands[0][5, 5] == 1500


def test_a_scene_larger_than_the_free_memory_is_read_by_rows(tmp_path, monkeypatch):
    """When the scene does not fit the computer's free memory, the steps read it by rows (only the tiles they need)
    and give the same band math, k-means classes and principal components as with the scene in memory; the page
    shows it band by band and reads a clicked pixel's values from its row."""
    import tifffile

    from astrowb.engine import parallel
    from astrowb.engine.steps import execute
    from astrowb.remotesensing import raster

    rng = np.random.default_rng(3)
    ny, nx = 700, 530
    cls = np.add.outer(np.arange(ny) // 90, np.arange(nx) // 70) % 4
    base = rng.normal(0, 1, (4, 5)) * 400 + 2000
    cube = (base[cls].transpose(2, 0, 1) + rng.normal(0, 60, (5, ny, nx))).astype(np.uint16)
    cube[:, :7, :9] = 0  # no data
    scale = (10.0, 10.0, 0.0)
    tie = (0.0, 0.0, 0.0, 500000.0, 4400000.0, 0.0)
    keys = (1, 1, 0, 3, 1024, 0, 1, 1, 1025, 0, 1, 1, 3072, 0, 1, 32636)
    path = tmp_path / "scene.tif"
    tifffile.imwrite(path, cube, tile=(128, 128), compression="zlib", planarconfig="separate",
                     extratags=[(33550, "d", 3, scale, True), (33922, "d", 6, tie, True), (34735, "H", 16, keys, True),
                                (42113, "s", 0, "0", True)])  # fmt: skip

    class Ctx:
        def progress(self, *a, **k):
            pass

        def check(self):
            pass

    def products(tag):
        out = {}
        for sid, inp, par in (("rs.expression", {"expression": "(B4 - B3) / (B4 + B3)"}, {}),
                              ("rs.classify", {}, {"k": 4}), ("rs.pca", {}, {"n": 3})):  # fmt: skip
            res = execute(sid, {"raster": str(path), "output": str(tmp_path / f"{sid}_{tag}.tif")} | inp, par, Ctx())
            out[sid] = tifffile.imread(res["product"]["path"]).astype(np.float64)
        return out

    whole = products("whole")
    monkeypatch.setattr(parallel, "available_memory", lambda: 10_000_000)  # 10 MB free
    assert isinstance(raster.load(str(path)), raster.Scene)
    by_rows = products("rows")
    for sid in whole:
        np.testing.assert_allclose(by_rows[sid], whole[sid], rtol=1e-5, atol=1e-5, equal_nan=True, err_msg=sid)
    sc = raster.load(str(path))
    whole_r = raster.read(str(path))
    np.testing.assert_array_equal(sc.band(2), whole_r.band(2))
    assert sc.pixel(300, 400).tolist() == whole_r.bands[:, 400, 300].tolist()
    assert sc.map_xy(0.5, 0.5) == whole_r.map_xy(0.5, 0.5)

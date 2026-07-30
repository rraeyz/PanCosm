"""General image operations: pixel values and the celestial WCS follow every geometric change."""

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS

from astrowb.io import process


def solved(ny=40, nx=50):
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [150.0, 20.0]
    w.wcs.crpix = [25.0, 20.0]
    w.wcs.cd = [[-2e-4, 1e-5], [1.5e-5, 2e-4]]
    data = np.arange(ny * nx, dtype=np.float32).reshape(ny, nx)
    return data, w.to_header()


@pytest.mark.parametrize(
    "op, args",
    [
        ("flip", {"axis": "x"}),
        ("flip", {"axis": "y"}),
        ("rotate90", {"k": 1}),
        ("rotate90", {"k": 3}),
        ("crop", {"x0": 5, "x1": 30, "y0": 7, "y1": 33}),
        ("bin", {"factor": 2}),
    ],
)
def test_geometry_keeps_sky_positions(op, args):
    data, h = solved()
    out, h2 = process.OPERATIONS[op](data, h, **args)
    w1, w2 = WCS(h), WCS(h2)
    # every output pixel shows the sky position its source pixel had (bin: block centres)
    for y2, x2 in [(0, 0), (out.shape[0] - 1, out.shape[1] - 1), (3, 8)]:
        sky = w2.pixel_to_world(x2, y2)
        if op == "bin":
            assert out[y2, x2] == pytest.approx(data[2 * y2 : 2 * y2 + 2, 2 * x2 : 2 * x2 + 2].mean())
            assert sky.separation(w1.pixel_to_world(2 * x2 + 0.5, 2 * y2 + 0.5)).arcsec < 1e-3
        else:
            yy, xx = np.argwhere(data == out[y2, x2])[0]  # pixel values are unique: find the source pixel
            assert sky.separation(w1.pixel_to_world(xx, yy)).arcsec < 1e-3


def test_filters_and_pixel_math():
    rng = np.random.default_rng(0)
    img = rng.normal(100, 5, (64, 64)).astype(np.float32)
    h = fits.Header()
    g, _ = process.gaussian(img, h, 2.0)
    assert np.std(g) < 0.3 * np.std(img) and g.mean() == pytest.approx(img.mean(), abs=0.5)
    m, _ = process.median(img, h, 3)
    assert np.std(m) < np.std(img)
    yy, xx = np.mgrid[:128, :128]
    noise = rng.normal(100, 5, (128, 128))
    sky = 50 + 0.5 * xx + 0.3 * yy + 0.002 * (xx - 60) ** 2
    galaxy = 300 * np.exp(-((xx - 90) ** 2 + (yy - 90) ** 2) / (2 * 6.0**2))  # spills over ~4 of 64 boxes
    b, _ = process.subtract_background((noise + sky + galaxy).astype(np.float32), h, 16)
    b = b - galaxy  # what is left of the sky model error
    # the whole smooth level (100 + gradient) is background: what is left is flat and near zero
    blocks = np.median(b.reshape(8, 16, 8, 16), axis=(1, 3))
    assert abs(np.median(b)) < 1 and np.ptp(blocks) < 3
    out, _ = process.pixel_math("A - 0.5 * B", {"A": img, "B": 2 * img}, h)
    assert np.allclose(out, 0)
    with pytest.raises(ValueError):
        process.pixel_math("A + B", {"A": img, "B": img[:10]}, h)
    with pytest.raises(ValueError):
        process.crop(img, h, 10, 5, 0, 10)


def test_process_step_writes_new_file(tmp_path):
    from astrowb.engine.steps import execute

    data, h = solved()
    src = tmp_path / "img.fits"
    fits.PrimaryHDU(data, h).writeto(src)

    class Ctx:
        def progress(self, *a):
            pass

    out = execute("image.process", {"image": str(src), "operation": "bin"}, {"args": {"factor": 2}}, Ctx())["image"]
    again = execute("image.process", {"image": str(src), "operation": "bin"}, {"args": {"factor": 2}}, Ctx())["image"]
    assert out != again and fits.getdata(out).shape == (20, 25)
    assert "bin" in str(fits.getheader(out)["HISTORY"])
    pm = execute(
        "image.process",
        {"image": str(src), "operation": "pixel_math", "others": [str(src)]},
        {"args": {"expression": "A - B"}},
        Ctx(),
    )["image"]
    assert np.all(fits.getdata(pm) == 0)


def _stars(fwhm, shape=(72, 72), sky=100.0):
    from astrowb.io.process import gaussian_psf

    img = np.full(shape, sky)
    psf = gaussian_psf(fwhm, 31)
    for y, x, f in ((20, 20, 5e4), (40, 45, 2e4), (15, 50, 1e4)):
        img[y - 15 : y + 16, x - 15 : x + 16] += f * psf
    return img


def _fwhm(img, y, x, sky=100.0):
    """FWHM from the second moment of a star (Gaussian: 2.3548 sigma)."""
    cut = img[y - 8 : y + 9, x - 8 : x + 9] - sky
    yy, xx = np.mgrid[-8:9, -8:9]
    return 2.3548 * np.sqrt(np.sum(cut * (xx**2 + yy**2)) / cut.sum() / 2)


def test_richardson_lucy_sharpens_and_keeps_flux():
    from astrowb.io.process import deconvolve

    img = _stars(4.0)
    out, _ = deconvolve(img, fits.Header(), fwhm=4.0, iterations=30)
    assert _fwhm(out, 20, 20) < 0.6 * _fwhm(img, 20, 20)
    assert abs(out.sum() / img.sum() - 1) < 1e-3
    assert abs(np.median(out) - 100) < 1


def test_kernel_filters_and_ddp():
    from astrowb.io.process import ddp, kernel_filter

    flat = np.full((20, 20), 7.0)
    for kind in ("lowpass", "highpass"):
        assert np.allclose(kernel_filter(flat, fits.Header(), kind)[0], 7.0)  # both keep a flat level
    for kind in ("laplacian", "edge_x", "edge_y", "sobel"):
        assert np.allclose(kernel_filter(flat, fits.Header(), kind)[0], 0.0)
    step = np.zeros((20, 20))
    step[:, 10:] = 1.0
    sob = kernel_filter(step, fits.Header(), "sobel")[0]
    assert sob[10, 9:11].min() > 3 and sob[10, :8].max() == 0  # the edge is found, flat parts are zero
    img = _stars(3.0)
    out, _ = ddp(img, fits.Header())
    bright = img[20, 20] - 100
    assert out.max() < 0.2 * bright and np.median(out) == 0  # cores compressed, sky at zero
    assert np.isclose(ddp(img, fits.Header(), breakpoint=1e9)[0][20, 20], bright, rtol=1e-3)  # a >> x: linear


def test_histogram_matching(tmp_path):
    from astrowb.io.process import match_histogram

    rng = np.random.default_rng(6)
    ref = rng.normal(1000, 50, (60, 80)).astype(np.float32)
    path = tmp_path / "ref.fits"
    fits.PrimaryHDU(ref).writeto(path)
    img = rng.exponential(3.0, (40, 50))
    img[3, 4] = np.nan
    out, _ = match_histogram(img, fits.Header(), str(path))
    vals = out[np.isfinite(out)]
    assert np.isnan(out[3, 4]) and vals.size == img.size - 1
    assert abs(np.mean(vals) - 1000) < 3 and abs(np.std(vals) - 50) < 3  # the reference's distribution
    order_in, order_out = np.argsort(img[np.isfinite(img)]), np.argsort(vals)
    assert np.array_equal(order_in, order_out)  # brightness order kept: brighter pixels stay brighter


def test_batch_conversion(tmp_path):
    import tifffile
    from PIL import Image

    from astrowb.engine.steps import execute

    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    paths = []
    for i in range(3):
        p = tmp_path / f"light_{i}.fits"
        fits.PrimaryHDU(np.random.default_rng(i).normal(1000, 10, (20, 30)).astype(np.float32)).writeto(p)
        paths.append(str(p))
    out = execute("image.convert", {"images": paths, "output_dir": str(tmp_path / "png")}, {}, Ctx())["written"]
    from pathlib import Path

    assert [Path(p).name for p in out] == ["light_0.png", "light_1.png", "light_2.png"]
    assert Image.open(out[0]).size == (30, 20)
    again = execute("image.convert", {"images": paths[:1], "output_dir": str(tmp_path / "png")}, {}, Ctx())["written"]
    assert Path(again[0]).name == "light_0_2.png"  # never overwrites
    tif = execute("image.convert", {"images": paths[:1], "output_dir": str(tmp_path / "t")}, {"fmt": "tif"}, Ctx())
    assert np.allclose(np.flipud(tifffile.imread(tif["written"][0])), fits.getdata(paths[0]))  # the data themselves


def test_unreadable_wcs_is_removed_not_left_wrong():
    import numpy as np
    from astropy.io import fits

    from astrowb.io import process

    h = fits.Header({"CTYPE1": "RA---XYZ", "CTYPE2": "DEC--XYZ", "CRPIX1": 10.0, "CRPIX2": 5.0, "CRVAL1": 30.0})
    h["CRVAL2"], h["CD1_1"], h["CD2_2"], h["OBJECT"] = 40.0, -1e-4, 1e-4, "M1"
    _, out = process.flip(np.zeros((20, 30)), h, "x")
    assert "CRPIX1" not in out and "CTYPE1" not in out and "CD1_1" not in out and out["OBJECT"] == "M1"
    assert "plate-solve again" in str(out["HISTORY"])

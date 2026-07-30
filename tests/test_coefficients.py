import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS
from photutils.psf import CircularGaussianPRF

from astrowb.photometry import coefficients as co


def test_extinction_from_constant_stars():
    rng = np.random.default_rng(2)
    x = np.linspace(1.1, 2.3, 60)  # the star sets during the series
    m0 = np.array([10.0, 11.0, 11.7, 12.3])
    m = m0[None, :] + 0.21 * x[:, None] + rng.normal(0, 0.005, (60, 4))
    m[17, 2] += 0.5  # a cosmic ray
    k = co.extinction(x, 10 ** (-0.4 * m))
    assert k["k"] == pytest.approx(0.21, abs=3 * k["k_err"] + 0.002) and k["n"] == 239
    with pytest.raises(ValueError, match="airmass"):
        co.extinction(np.full(10, 1.2), np.ones((10, 2)))


def test_transformation_coefficients():
    rng = np.random.default_rng(3)
    V = rng.uniform(10, 14, 40)
    BV = rng.uniform(-0.1, 1.6, 40)
    B = V + BV
    # instrument: b - v = (B - V) / 1.08 + 0.3;  v = V - (-0.04 (B-V) + 2.1);  b from b - v
    v = V - (-0.04 * BV + 2.1) + rng.normal(0, 0.008, 40)
    b = v + BV / 1.08 + 0.3 + rng.normal(0, 0.008, 40)
    out = co.transformation(B, V, b, v, ("B", "V"))
    assert out["tbv"]["value"] == pytest.approx(1.08, abs=0.02)
    assert out["tv"]["value"] == pytest.approx(-0.04, abs=0.015) and out["n"] == 40


def _image(path, wcs, stars, flux_scale, rng):
    yy, xx = np.mgrid[:150, :180]
    img = np.full((150, 180), 300.0)
    x, y = wcs.world_to_pixel_values(stars[:, 0], stars[:, 1])
    for xi, yi, f in zip(x, y, stars[:, 2] * flux_scale, strict=True):
        img += CircularGaussianPRF(flux=f, x_0=xi, y_0=yi, fwhm=3.0)(xx, yy)
    h = wcs.to_header()
    h["EXPTIME"], h["DATE-OBS"] = 30.0, "2026-11-15T20:00:00"
    fits.PrimaryHDU(rng.poisson(img).astype(np.float32), h).writeto(path)
    return str(path)


def test_standard_field_from_two_solved_images(tmp_path):
    rng = np.random.default_rng(4)
    w = WCS(naxis=2)
    w.wcs.ctype, w.wcs.crval, w.wcs.crpix = ["RA---TAN", "DEC--TAN"], [100.0, 20.0], [90.5, 75.5]
    w.wcs.cdelt = [-1.0 / 3600, 1.0 / 3600]
    xs, ys = np.meshgrid(np.linspace(25, 155, 6), np.linspace(25, 125, 5))
    ra, dec = w.pixel_to_world_values(xs.ravel(), ys.ravel())
    V = rng.uniform(11, 13.5, ra.size)
    BV = rng.uniform(0.0, 1.4, ra.size)
    fv = 10 ** (-0.4 * (V - 24))  # bright standards: 1-3 mmag photon noise
    fb = 10 ** (-0.4 * (V + BV / 1.1 - 23.6))  # instrument: b - v = (B-V)/1.1 + const
    a = _image(tmp_path / "b.fits", w, np.column_stack([ra, dec, fb]), 1.0, rng)
    w2 = w.deepcopy()
    w2.wcs.crpix = [92.0, 73.0]  # the second image is shifted
    bimg = _image(tmp_path / "v.fits", w2, np.column_stack([ra, dec, fv]), 1.0, rng)

    def fake_catalogue(sky, bands):
        from astropy.coordinates import SkyCoord

        idx, sep, _ = sky.match_to_catalog_sky(SkyCoord(ra, dec, unit="deg"))
        return {"B": (V + BV)[idx].tolist(), "V": V[idx].tolist()}

    d = co.standard_stars(a, bimg, "B", "V", catalogue=fake_catalogue)
    out = co.transformation(d["cat_a"], d["cat_b"], d["inst_a"], d["inst_b"], ("B", "V"))
    assert out["n"] >= 25 and out["tbv"]["value"] == pytest.approx(1.1, abs=0.03)


def test_coefficients_dialog(qtbot):
    from astrowb.ui.coefficients_dialog import CoefficientsDialog

    rng = np.random.default_rng(5)
    x = np.linspace(1.05, 1.9, 40)
    comp = 10 ** (-0.4 * (np.array([11.0, 12.0])[None, :] + 0.3 * x[:, None] + rng.normal(0, 0.003, (40, 2))))
    dlg = CoefficientsDialog({"airmass": x.tolist(), "comp_flux": comp.tolist()})
    qtbot.addWidget(dlg)
    k = dlg.compute_extinction()
    assert abs(k["k"] - 0.3) < 0.01 and "k = 0.3" in dlg.ext_result.text()
    V = rng.uniform(10, 13, 20)
    BV = rng.uniform(0, 1.5, 20)
    stars = {"cat_a": (V + BV).tolist(), "cat_b": V.tolist(), "inst_a": (V + BV / 1.05 - 20).tolist()}
    stars["inst_b"] = (V - 20.0).tolist()
    out = {
        "transformation": co.transformation(
            stars["cat_a"], stars["cat_b"], stars["inst_a"], stars["inst_b"], ("B", "V")
        )
    }
    dlg.show_transformation(out | {"stars": stars})
    assert "Tbv = 1.05" in dlg.tr_result.text()
    assert not CoefficientsDialog(None).ext_button.isEnabled()

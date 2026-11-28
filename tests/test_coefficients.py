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
    assert [s.name for s in dlg.plot.figure.panels[0].series][-1] == "Fit" and dlg.plot.figure.panels[0].y.invert
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
    assert "Tbv = 1.05" in dlg.tr_result.text() and len(dlg.plot.figure.panels[0].series[0].x) == 20
    assert not CoefficientsDialog(None).ext_button.isEnabled()


def _night(rng, k=0.25, k2=-0.03, colours=(0.2, 0.5, 0.8, 1.1, 1.4)):
    x = np.linspace(1.1, 2.4, 80)
    c = np.array(colours)
    m = np.linspace(10, 12, len(c))[None] + k * x[:, None] + k2 * c[None] * x[:, None]
    return x, c, 10 ** (-0.4 * (m + rng.normal(0, 0.004, m.shape)))


def test_second_order_extinction_recovered():
    x, c, f = _night(np.random.default_rng(5))
    o = co.extinction(x, f, c, second_order=True)
    assert o["k"] == pytest.approx(0.25, abs=3 * o["k_err"]) and o["k2"] == pytest.approx(-0.03, abs=3 * o["k2_err"])
    assert o["k2_err"] > 0


def test_second_order_off_is_the_old_fit_and_narrow_colour_span_raises():
    x, c, f = _night(np.random.default_rng(6), k2=0.0)
    o = co.extinction(x, f)
    assert "k2" not in o and o["k"] == pytest.approx(0.25, abs=3 * o["k_err"])
    with pytest.raises(ValueError, match="colours do not differ"):
        co.extinction(x, f, np.full(5, 0.7), second_order=True)
    with pytest.raises(ValueError, match="colours do not differ"):
        co.extinction(x, f, None, second_order=True)


def test_transformed_magnitudes_box_needs_the_comparison_colours(qtbot):
    """PHO-35: with the comparison stars' B − V (the page's catalogue look-up) the box gives transform.transformed per
    frame with the dialog's colour term; without them (or with Gaia-only colours) it is disabled and says why."""
    from astrowb.photometry.transform import transformed
    from astrowb.ui.coefficients_dialog import CoefficientsDialog

    rng = np.random.default_rng(2)
    comp = 10 ** (-0.4 * (np.array([11.0, 12.0])[None, :] + rng.normal(0, 0.003, (30, 2))))
    rel = 10 ** (-0.4 * rng.normal(0.5, 0.01, 30))
    lc = {"time": np.linspace(0.3, 0.5, 30).tolist(), "rel_flux": rel.tolist(), "rel_flux_err": [0.002] * 30,
          "comp_flux": comp.tolist()}  # fmt: skip
    cat = {"filter": "V", "target": {"mag": 11.5, "colour": 0.9, "source": "APASS DR9"},
           "comps": [{"mag": 11.0, "colour": 0.4, "source": "APASS DR9"},
                     {"mag": 12.0, "colour": 1.2, "source": "Gaia DR3 GSPC"}]}  # fmt: skip
    dlg = CoefficientsDialog(lc, catalog=cat)
    qtbot.addWidget(dlg)
    assert dlg.transform_box.isEnabled() and dlg.target_colour.text() == "0.900"
    dlg.transform_box.setChecked(True)  # no colour term yet: it says so and unticks
    assert not dlg.transform_box.isChecked() and "No colour term for V" in dlg.transform_note.text()
    dlg.result = {"transformation": {"tv": {"value": -0.08, "error": 0.01}}}
    dlg.transform_box.setChecked(True)
    want, _ = transformed(lc, [11.0, 12.0], [0.4, 1.2], 0.9, -0.08, 0.01)
    assert np.allclose(dlg.transformed["mag"], want) and "V on 30 frames" in dlg.transform_note.text()
    dlg.transform_box.setChecked(False)
    assert dlg.transformed is None
    for comps in ([cat["comps"][0], None], [cat["comps"][0], {"mag": 12.0, "colour": 0.7, "source": "Gaia DR3"}]):
        other = CoefficientsDialog(lc, catalog=cat | {"comps": comps})
        qtbot.addWidget(other)
        assert not other.transform_box.isEnabled() and "B − V colours" in other.transform_box.toolTip()
    assert not CoefficientsDialog(None).transform_box.isEnabled()

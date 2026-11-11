"""What is in the field (photometry.field): a frame solved against Gaia without a plate solver, the known variable
stars in it, the OBJECT of its header checked, comparison stars from the catalogue (the owner's NY Vir night: the
files named a star 48 deg away and nothing said so)."""

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS

from astrowb.photometry import field

RA0, DEC0 = 204.70, -2.03
SCALE = 206.264806 * 30.0 / 10000.0  # arcsec per pixel: XPIXSZ 30 µm, FOCALLEN 10 m


def _sky(n=300, seed=4):
    rng = np.random.default_rng(seed)
    ra = RA0 + rng.uniform(-0.25, 0.25, n) / np.cos(np.radians(DEC0))
    dec = DEC0 + rng.uniform(-0.25, 0.25, n)
    g = rng.uniform(10.0, 17.5, n)
    cat = {"ra": ra, "dec": dec, "pmra": np.zeros(n), "pmdec": np.zeros(n), "gmag": g,
           "bp_rp": rng.uniform(0.5, 1.5, n), "variable": np.zeros(n)}  # fmt: skip
    cat["ra"][0], cat["dec"][0] = RA0 + 0.02, DEC0 - 0.01  # the target, inside the frame
    cat["bp_rp"][0] = -0.4  # a hot subdwarf, bluer than every other star
    cat["gmag"][0] = 13.4
    return cat


def _frame(cat, angle=30.0, flip=True, shape=(800, 900)):
    """A frame of the catalogue: rotated by angle, mirrored when flip, Gaussian stars, sky and noise."""
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [RA0, DEC0]
    w.wcs.crpix = [shape[1] / 2, shape[0] / 2]
    c, s = np.cos(np.radians(angle)), np.sin(np.radians(angle))
    k = SCALE / 3600
    w.wcs.cd = np.array([[-k * c, k * s], [k * s, k * c]]) @ np.diag([-1.0 if flip else 1.0, 1.0])
    x, y = w.all_world2pix(cat["ra"], cat["dec"], 0)
    yy, xx = np.mgrid[: shape[0], : shape[1]]
    img = np.full(shape, 500.0)
    for xi, yi, g in zip(x, y, cat["gmag"], strict=True):
        if -10 < xi < shape[1] + 10 and -10 < yi < shape[0] + 10:
            sl = (slice(max(0, int(yi) - 12), int(yi) + 13), slice(max(0, int(xi) - 12), int(xi) + 13))
            img[sl] += (
                10 ** (-0.4 * (g - 22))
                / (2 * np.pi * 2.0**2)
                * np.exp(-((xx[sl] - xi) ** 2 + (yy[sl] - yi) ** 2) / (2 * 2.0**2))
            )
    img += np.random.default_rng(1).normal(0, 8, shape)
    return img, w, x, y


def _header(off_arcmin=4.0):
    from astropy.coordinates import SkyCoord

    c = SkyCoord(RA0 + off_arcmin / 60 / np.cos(np.radians(DEC0)), DEC0 + 0.5 * off_arcmin / 60, unit="deg")
    ra, dec = c.to_string("hmsdms", sep=":").split()
    return fits.Header({"OBJECT": "NSVS07826147", "OBJCTRA": ra, "OBJCTDEC": dec, "FOCALLEN": 10000.0,
                        "XPIXSZ": 30.0, "DATE-OBS": "2016-01-01T00:00:00"})  # fmt: skip


def test_a_turned_mirrored_frame_is_solved_against_the_catalogue(tmp_path):
    cat = _sky()
    img, truth, x, y = _frame(cat)
    assert field.pixel_scale(_header()) == pytest.approx(SCALE, rel=1e-3)
    sol = field.solve(img, _header(), cat)
    assert sol["matched"] >= 10 and sol["rms_px"] < 0.3  # about 25 catalogue stars fall on this small frame
    assert sol["scale"] == pytest.approx(SCALE, rel=2e-3)
    px, py = sol["wcs"].world_to_pixel_values(cat["ra"], cat["dec"])
    inside = (x > 20) & (x < 880) & (y > 20) & (y < 780)
    assert np.allclose(px[inside], x[inside], atol=0.5) and np.allclose(py[inside], y[inside], atol=0.5)


def test_the_field_names_its_variable_and_says_the_object_is_elsewhere(tmp_path):
    cat = _sky()
    img, _, x, y = _frame(cat)
    fits.PrimaryHDU(img.astype(np.float32), _header()).writeto(tmp_path / "f.fits")
    ny_vir = {"name": "NY Vir", "ra": float(cat["ra"][0]), "dec": float(cat["dec"][0]), "mag": 13.3}
    out = field.identify(tmp_path / "f.fits", catalogue=cat, variables=[ny_vir], resolve=lambda name: (233.456, 37.991))
    (v,) = out["variables"]
    assert v["name"] == "NY Vir" and abs(v["x"] - x[0]) < 0.3 and abs(v["y"] - y[0]) < 0.3
    assert out["object"]["name"] == "NSVS07826147" and not out["object"]["in_field"]
    assert out["object"]["distance_deg"] == pytest.approx(48.0, abs=0.5)
    picks = field.comparison_stars(out, (v["x"], v["y"]), img, saturation=65535, n=4)
    assert len(picks["stars"]) == 4 and not picks["same_colour"]  # nothing as blue as the subdwarf
    g = [s[2] for s in picks["stars"]]
    assert all(abs(gi - 13.4) <= 2.5 for gi in g)
    with pytest.raises(ValueError, match="not a Gaia star"):
        field.comparison_stars(out, (5.0, 5.0), img)


def test_without_pointing_or_scale_the_reason_is_given():
    img = np.zeros((100, 100))
    with pytest.raises(ValueError, match="no pointing"):
        field.solve(img, fits.Header({"FOCALLEN": 1000.0, "XPIXSZ": 9.0}), {})
    with pytest.raises(ValueError, match="pixel scale is unknown"):
        field.solve(img, fits.Header({"OBJCTRA": "13 38 48", "OBJCTDEC": "-02 01 49"}), {})


def test_photometry_page_shows_the_field_and_makes_a_variable_the_target(qtbot, tmp_path):
    from astrowb.ui.photometry_page import PhotometryPage

    cat = _sky()
    img, w, x, y = _frame(cat)
    fits.PrimaryHDU(img.astype(np.float32), _header()).writeto(tmp_path / "f.fits")
    ny_vir = {"name": "NY Vir", "ra": float(cat["ra"][0]), "dec": float(cat["dec"][0]), "mag": 13.3}
    out = field.identify(tmp_path / "f.fits", catalogue=cat, variables=[ny_vir], resolve=lambda name: (233.456, 37.991))
    page = PhotometryPage()
    qtbot.addWidget(page)
    with qtbot.waitSignal(page.field_requested) as asked:
        page.set_images([str(tmp_path / "f.fits")])
    assert asked.args == [str(tmp_path / "f.fits")]
    page.show_field(out)
    text = page.field_label.text()
    assert "OBJECT = NSVS07826147" in text and "48." in text and "1 known variable star" in text
    assert page.variables.count() == 1 and not page.make_target.isHidden()
    page.make_target.click()
    assert np.allclose(page.target, (x[0], y[0]), atol=0.3) and page.ref == 0
    from astropy.coordinates import SkyCoord

    typed = SkyCoord(page.coord.text(), unit=("hourangle", "deg"))
    assert typed.separation(SkyCoord(ny_vir["ra"], ny_vir["dec"], unit="deg")).arcsec < 1
    page._clear()
    page._clicked(x[5], y[5])  # a target marked by hand: its sky position from the solution
    typed = SkyCoord(page.coord.text(), unit=("hourangle", "deg"))
    assert typed.separation(SkyCoord(cat["ra"][5], cat["dec"][5], unit="deg")).arcsec < 1
    page.field_failed("the stars of the frame do not match the Gaia stars around its pointing")
    assert "not identified" in page.field_label.text() and page.field is None


def test_images_then_measure_is_the_whole_of_it(qtbot, tmp_path):
    """The star the files name becomes the target, the comparison stars and then the radii are asked for without a
    press; a suggestion that arrives after stars were clicked by hand is dropped."""
    from astrowb.ui.photometry_page import PhotometryPage

    cat = _sky()
    img, w, x, y = _frame(cat)
    fits.PrimaryHDU(img.astype(np.float32), _header()).writeto(tmp_path / "f.fits")
    page = PhotometryPage()
    qtbot.addWidget(page)
    page.set_images([str(tmp_path / "f.fits")])
    obj = {"name": "NY Vir", "known": True, "ra": float(cat["ra"][0]), "dec": float(cat["dec"][0]),
           "x": float(x[0]), "y": float(y[0]), "in_field": True, "distance_deg": 0.0}  # fmt: skip
    with qtbot.waitSignal(page.suggest_requested) as asked:
        page.show_field(
            {"matched": 50, "scale": 0.74, "object": obj, "variables": [], "header": w.to_header().tostring()}
        )
    assert np.allclose(page.target, (x[0], y[0])) and np.allclose(asked.args[1], (x[0], y[0]))
    with qtbot.waitSignal(page.apertures_requested) as radii:
        page.set_comparisons([(x[1], y[1]), (x[2], y[2])])
    assert len(radii.args[2]) == 2 and len(page.comps) == 2
    page.edit("clear", page._clear)
    page._clicked(x[3], y[3])  # a new target by hand asks again
    page._clicked(x[4], y[4])  # and a comparison clicked before the answer came
    page.set_comparisons([(x[1], y[1])])
    assert page.comps == [(x[4], y[4])]
    page.undo_stack.undo()  # the hand-clicked comparison, then the target, come off one by one
    assert page.comps == [] and page.target is not None

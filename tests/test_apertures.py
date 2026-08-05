"""Aperture and sky annulus chosen from the stars: simulated stars of known FWHM and brightness."""

import numpy as np
import pytest
from astropy.io import fits

from astrowb.photometry.aperture import SKY_RATIO, choose_apertures, seeing_fwhm
from astrowb.photometry.lightcurve import light_curve

STARS = [(60.3, 70.6, 2e5), (140.2, 60.1, 1e5), (100.7, 150.4, 3e5), (40.0, 160.0, 5e4)]


def field(fwhm, stars=STARS, sky=300.0, beta=None, seed=1, shape=(200, 200)):
    """Poisson + read noise image; Gaussian stars, or Moffat stars of the given beta."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[: shape[0], : shape[1]]
    img = np.full(shape, sky)
    for x, y, f in stars:
        r2 = (xx - x) ** 2 + (yy - y) ** 2
        if beta is None:
            s = fwhm / 2.3548
            img += f / (2 * np.pi * s**2) * np.exp(-r2 / (2 * s**2))
        else:
            alpha = fwhm / (2 * np.sqrt(2 ** (1 / beta) - 1))
            img += f * (beta - 1) / (np.pi * alpha**2) * (1 + r2 / alpha**2) ** -beta
    return rng.poisson(img).astype(float) + rng.normal(0, 8, shape)


@pytest.mark.parametrize("fwhm,beta", [(2.8, None), (4.7, None), (7.0, None), (4.0, 3.0)])
def test_three_rings_follow_the_stars(fwhm, beta):
    a = choose_apertures(field(fwhm, beta=beta), [s[:2] for s in STARS])
    assert a["fwhm"] == pytest.approx(fwhm, rel=0.06)
    assert 1.0 * a["fwhm"] - 0.01 <= a["r_ap"] <= 3.0 * a["fwhm"] + 0.01
    snr = np.interp([0.6 * a["r_ap"], a["r_ap"], 2.0 * a["r_ap"]], a["radii"], a["snr"])
    assert snr[1] >= 0.98 * max(snr)  # the aperture sits on the S/N maximum (or the 1 FWHM floor)
    assert a["r_in"] >= 3.0 * a["fwhm"] - 0.01 and a["r_in"] > a["r_ap"]  # a gap between rings 1 and 2
    assert np.interp(a["r_in"], a["radii"], a["encircled"]) >= 0.99  # the star's light has ended at ring 2
    assert a["r_out"] ** 2 - a["r_in"] ** 2 == pytest.approx(SKY_RATIO * a["r_ap"] ** 2, rel=0.01)


def test_faint_target_gets_a_smaller_aperture():
    # Howell (1989): background-limited stars have their best S/N in a smaller aperture than bright ones
    bright = choose_apertures(field(5.0, stars=[(100.0, 100.0, 1e7)]), [(100.0, 100.0)])
    faint = choose_apertures(field(5.0, stars=[(100.0, 100.0, 3e3)]), [(100.0, 100.0)])
    assert faint["best_snr_radius"] < bright["best_snr_radius"]
    assert faint["encircled_at_aperture"] < bright["encircled_at_aperture"]


def test_radii_follow_the_seeing(tmp_path):
    fwhms = (3.0, 3.5, 4.5, 6.0)
    paths = []
    for i, f in enumerate(fwhms):
        h = fits.Header({"DATE-OBS": f"2026-11-15T20:{i:02d}:00", "EXPTIME": 30.0})
        fits.PrimaryHDU(field(f, seed=i).astype(np.float32), h).writeto(tmp_path / f"f{i}.fits")
        paths.append(tmp_path / f"f{i}.fits")
    stars = [s[:2] for s in STARS]
    assert seeing_fwhm(fits.getdata(paths[0]), stars) == pytest.approx(3.0, rel=0.06)
    lc = light_curve(paths, stars[0], stars[1:], 0, 0, 0, auto=True, follow_seeing=True)
    r_ap = np.array([r[0] for r in lc["radii"]])
    assert r_ap[0] == lc["apertures"]["r_ap"]
    assert r_ap / r_ap[0] == pytest.approx(np.array(fwhms) / fwhms[0], rel=0.08)
    assert np.std(lc["rel_flux"]) / np.mean(lc["rel_flux"]) < 0.01  # same light fraction for all stars
    fixed = light_curve(paths, stars[0], stars[1:], 5.0, 12.0, 18.0)
    assert all(r == [5.0, 12.0, 18.0] for r in fixed["radii"]) and "apertures" not in fixed


def test_photometry_page_draws_three_rings_and_the_profile(qtbot):
    from astrowb.ui.workspaces import PhotometryPage

    page = PhotometryPage()
    qtbot.addWidget(page)
    page.viewer.set_image(field(4.0))
    page.images = ["x.fits"]
    page._clicked(60.3, 70.6)
    page._clicked(140.2, 60.1)
    assert page.apertures_button.isEnabled()
    a = choose_apertures(field(4.0), [(60.3, 70.6), (140.2, 60.1)])
    page.show_apertures(a)
    assert (page.r_ap.value(), page.r_in.value(), page.r_out.value()) == (a["r_ap"], a["r_in"], a["r_out"])
    real = [m for m in page.viewer._markers if m.data(0) is None]  # without the fixed-size rings
    assert len(real) == 2 * 3 * 2  # two stars x three rings, each a circle and a label
    assert "FWHM" in page.result.text() and page.plot.figure.axes


def test_scintillation_follows_osborn_2015():
    from astrowb.photometry.aperture import scintillation

    assert scintillation(1.0, 1.0, 1.0, 0.0) == pytest.approx(np.sqrt(10e-6 * 1.5**2), rel=1e-12)  # 0.474 %
    s = scintillation(0.4, 30.0, 1.0, 2500.0)
    assert scintillation(0.4, 120.0, 1.0, 2500.0) == pytest.approx(s / 2)  # 1 / sqrt(t)
    assert scintillation(0.4, 30.0, 2.0, 2500.0) == pytest.approx(s * 2**1.5)  # X^(3/2)
    assert scintillation(0.8, 30.0, 1.0, 2500.0) == pytest.approx(s * 2 ** (-2 / 3))  # D^(-2/3)
    with pytest.raises(ValueError):
        scintillation(0.0, 30.0, 1.0)


def test_light_curve_errors_include_scintillation(tmp_path):
    from astrowb.photometry.aperture import scintillation

    paths = []
    for i in range(3):
        site = {"SITELAT": 36.82, "SITELONG": 30.34, "SITEELEV": 2500.0, "OBJCTRA": "02 04 10", "OBJCTDEC": "+46 41 16"}
        h = fits.Header({"DATE-OBS": f"2026-11-15T20:{i:02d}:00", "EXPTIME": 10.0} | site)
        fits.PrimaryHDU(field(4.0, seed=i).astype(np.float32), h).writeto(tmp_path / f"f{i}.fits")
        paths.append(tmp_path / f"f{i}.fits")
    stars = [s[:2] for s in STARS]
    plain = light_curve(paths, stars[0], stars[1:], 6, 18, 24)
    assert plain["scintillation"] is None and plain["aperture_m"] is None  # no aperture known: nothing added
    lc = light_curve(paths, stars[0], stars[1:], 6, 18, 24, aperture_m=0.4)
    sig = scintillation(0.4, 10.0, lc["airmass"], 2500.0)
    assert lc["scintillation"] == pytest.approx(sig, rel=1e-9)
    f, e0, e1 = (np.asarray(x) for x in (plain["target_flux"], plain["target_flux_err"], lc["target_flux_err"]))
    assert e1**2 == pytest.approx(e0**2 + (sig * f) ** 2, rel=1e-9)  # added in quadrature
    assert lc["rel_flux"] == pytest.approx(plain["rel_flux"], rel=1e-12)  # the measurement itself is unchanged
    fits.setval(paths[0], "APTDIA", value=400.0)  # MaxIm / SGP / NINA write the aperture in mm
    assert light_curve(paths, stars[0], stars[1:], 6, 18, 24)["aperture_m"] == 0.4


@pytest.mark.parametrize("kind", ["defocused 40", "defocused 60", "donut"])
def test_centroids_of_defocused_stars(kind):
    """Exoplanet observers defocus: a star wider than the centroid box, or a donut with a dark centre, is still
    found to < 0.2 px (the Gaussian centroid in its 11-pixel box was 1.8 px off, or gave up)."""
    from astrowb.photometry.aperture import recenter

    rng = np.random.default_rng(4)
    yy, xx = np.mgrid[:400, :400]
    x0, y0 = 200.3, 199.6
    if kind == "donut":
        r = np.hypot(xx - x0, yy - y0)
        model = np.where((r > 15) & (r < 40), 800.0, 0.0)
    else:
        s = float(kind.split()[1]) / 2.3548
        model = 1e6 / (2 * np.pi * s * s) * np.exp(-((xx - x0) ** 2 + (yy - y0) ** 2) / (2 * s * s))
    img = rng.poisson(model + 100).astype(float)
    got = recenter(img, [[x0 + 1.5, y0 - 1.0]])[0]
    assert np.hypot(got[0] - x0, got[1] - y0) < 0.2, got


def test_suggested_comparisons_near_the_target_first():
    from astrowb.photometry.aperture import suggest_comparisons

    stars = [(100.0, 100.0, 1e5), (130.0, 120.0, 1e5), (320.0, 330.0, 1e5)]  # the target, a near and a far twin
    img = field(4.0, stars=stars, shape=(400, 400))
    picks = suggest_comparisons(img, (100.0, 100.0), r_out=20)
    assert len(picks) == 2 and picks[0] == pytest.approx((130.0, 120.0), abs=0.5)


def test_suggestion_says_what_it_chose(qtbot):
    from astrowb.ui.workspaces import PhotometryPage

    page = PhotometryPage()
    qtbot.addWidget(page)
    page.viewer.set_image(field(4.0))
    page.images = ["x.fits"]
    page._clicked(60.3, 70.6)
    page.set_comparisons([(140.2, 60.1), (100.7, 150.4)])
    assert page.result.text().startswith("2 comparison stars suggested") and "take it off" in page.result.text()
    page.set_comparisons([])
    assert page.result.text().startswith("No suitable comparison star")


def test_a_neighbour_in_the_target_wings_is_pointed_out(qtbot):
    # Qatar-1 b (LCO): light next to the target made radii that follow the seeing move the transit by 20 min
    stars = [(100.0, 100.0, 2e5), (300.0, 120.0, 2e5), (140.0, 300.0, 2e5), (320.0, 310.0, 2e5)]
    clean = choose_apertures(field(4.5, stars=stars, shape=(420, 420)), [s[:2] for s in stars])
    blended = choose_apertures(
        field(4.5, stars=stars + [(106.0, 105.0, 1.5e4)], shape=(420, 420)), [s[:2] for s in stars]
    )
    assert abs(clean["target_excess"]) < 0.005 and blended["target_excess"] > 0.01
    from astrowb.ui.workspaces import PhotometryPage

    page = PhotometryPage()
    qtbot.addWidget(page)
    page.show_apertures(blended)
    assert "something faint is next to it" in page.result.text()
    page.show_apertures(clean)
    assert "something faint" not in page.result.text()

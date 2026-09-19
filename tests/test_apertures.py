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
    assert len(real) == 2 * (3 + 1)  # two stars x three rings, and a label on the aperture (the dashed have none)
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


@pytest.mark.parametrize("x0", [50.0, 50.3, 50.5, 50.8])
def test_centroid_of_an_undersampled_star_next_to_a_hot_pixel(x0):
    """A star of FWHM 1.5 px (MicroObservatory, HAT-P-32: the 3x3 median filter halved its core and the centroid
    went 2 px off, the transit scatter rose from 0.012 to 0.017) is found, and a hot pixel beside it is ignored."""
    from astrowb.photometry.aperture import recenter

    rng = np.random.default_rng(5)
    yy, xx = np.mgrid[:100, :100]
    s = 1.5 / 2.3548
    model = 2e4 / (2 * np.pi * s * s) * np.exp(-((xx - x0) ** 2 + (yy - 49.6) ** 2) / (2 * s * s))
    img = rng.poisson(model + 360).astype(float)
    img[52, 53] = 6000.0
    got = recenter(img, [[x0 + 0.4, 49.6 - 0.3]])[0]
    assert np.hypot(got[0] - x0, got[1] - 49.6) < 0.2, got


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
    # a faint neighbour in the target's wings: radii that follow the seeing take a varying share of its light
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


def test_a_click_three_pixels_off_is_snapped_onto_the_star(tmp_path):
    # real LCO night: a position 2.7 px off Qatar-1 was kept (the 2.5 px limit between frames) and the aperture sat
    # off the star all night: 0.7 % differences against an independent photutils run, a transit 3-22 min off
    paths = []
    for i in range(3):
        h = fits.Header({"DATE-OBS": f"2026-11-15T20:{i:02d}:00", "EXPTIME": 30.0})
        fits.PrimaryHDU(field(4.5, seed=20 + i).astype(np.float32), h).writeto(tmp_path / f"f{i}.fits")
        paths.append(tmp_path / f"f{i}.fits")
    stars = [s[:2] for s in STARS]
    off = (stars[0][0] + 0.5, stars[0][1] + 2.8)
    lc = light_curve(paths, off, stars[1:3], 8, 16, 24)
    for xy in lc["xy"]:
        assert np.hypot(xy[0][0] - stars[0][0], xy[0][1] - stars[0][1]) < 0.3


def test_binned_frame_shift_is_close_enough_for_re_centring():
    from astrowb.photometry.aperture import frame_shift

    rng = np.random.default_rng(3)
    yy, xx = np.mgrid[0:1200, 0:1200]
    stars = rng.uniform(50, 1150, (60, 2))

    def field(dx, dy):
        img = rng.normal(100, 3, (1200, 1200)).astype(np.float32)
        for x, y in stars:
            img += 3000 * np.exp(-((xx - x - dx) ** 2 + (yy - y - dy) ** 2) / (2 * 2.0**2))
        return img

    a, b = field(0, 0), field(12.3, -7.6)
    dx, dy = frame_shift(a, b, binning=2)
    assert abs(dx - 12.3) < 0.3 and abs(dy + 7.6) < 0.3  # recenter (max 2.5 px) does the rest


def test_apertures_fit_a_small_tess_stamp():
    """A TESS target pixel file is 13 x 11 px: the profile had no sky 25 px away and the radii came out 200 px."""
    from astrowb.photometry.aperture import choose_apertures

    yy, xx = np.mgrid[0:13, 0:11]
    rng = np.random.default_rng(1)
    stamp = 2e5 * np.exp(-((xx - 5.8) ** 2 + (yy - 6.1) ** 2) / (2 * (1.6 / 2.355) ** 2)) + rng.normal(0, 30, (13, 11))
    c = choose_apertures(stamp, [(5.8, 6.1)], 1.0)
    assert 1.0 < c["fwhm"] < 2.5 and 1.5 <= c["r_ap"] <= 4.5 and c["r_ap"] < c["r_in"] < c["r_out"] <= 8.5


def test_light_curve_places_every_frame_against_the_first_and_leaves_out_lost_frames(tmp_path):
    """The owner's NY Vir night: frames were tracked one from the previous, so one wrong shift sent the apertures
    onto empty sky for the rest of the night, silently (negative fluxes, a plot that failed). Now every frame is
    placed against the first, the stars are checked on every frame, a rotated frame (meridian flip) is matched by
    its star pattern, and a frame without the stars (a cloud) is left out and named, with why."""
    many = [(60.3, 70.6, 2e5), (140.2, 60.1, 1e5), (100.7, 150.4, 3e5), (40.0, 160.0, 5e4)]
    many += [(25.0, 30.0, 8e4), (170.0, 120.0, 1.2e5), (90.0, 110.0, 6e4), (150.0, 175.0, 9e4), (120.0, 25.0, 7e4)]
    shifted = [(x + 12.0, y - 7.0, f) for x, y, f in many]
    frames = {
        "f0": field(4.0, many, seed=0),
        "f1": field(4.0, shifted, seed=1),
        "f2": field(4.0, many, seed=2)[::-1, ::-1],  # turned half round
        "f3": np.random.default_rng(3).normal(300.0, 17.0, (200, 200)),  # a cloud: no star at all
        "f4": field(4.0, [(x, y, f) for x, y, f in many if (x, y) != (60.3, 70.6)], seed=4),  # the target is gone
    }
    paths = []
    for i, (name, img) in enumerate(frames.items()):
        h = fits.Header({"DATE-OBS": f"2026-11-15T20:{i:02d}:00", "EXPTIME": 10.0})
        fits.PrimaryHDU(img.astype(np.float32), h).writeto(tmp_path / f"{name}.fits")
        paths.append(tmp_path / f"{name}.fits")
    stars = [s[:2] for s in many[:4]]
    lc = light_curve(paths, stars[0], stars[1:], 6, 18, 24)
    assert lc["file"] == ["f0.fits", "f1.fits", "f2.fits"]
    assert lc["lost"] == {"f3.fits": ["aligned"], "f4.fits": ["target"]}
    rel = np.asarray(lc["rel_flux"])
    assert np.allclose(rel, rel[0], rtol=0.02)  # the shifted and the turned frame measured on the stars
    assert np.allclose(lc["xy"][1][0], (60.3 + 12.0, 70.6 - 7.0), atol=0.3)
    assert np.allclose(lc["xy"][2][0], (199 - 60.3, 199 - 70.6), atol=0.3)


def test_light_curve_checks_frames_on_every_core_too(tmp_path, monkeypatch):
    """The same checks on the parallel path (24 frames or more): frames read in part around the stars are read
    whole and matched by their star pattern when the stars are not where the shifts put them."""
    import astrowb.engine.parallel as par

    monkeypatch.setattr(par, "workers", lambda: 2)
    many = [(60.3, 70.6, 2e5), (140.2, 60.1, 1e5), (100.7, 150.4, 3e5), (40.0, 160.0, 5e4)]
    many += [(25.0, 30.0, 8e4), (170.0, 120.0, 1.2e5), (90.0, 110.0, 6e4), (150.0, 175.0, 9e4), (120.0, 25.0, 7e4)]
    paths = []
    for i in range(26):
        if i == 10:
            img = np.random.default_rng(i).normal(300.0, 17.0, (200, 200))  # a cloud
        elif i == 20:
            img = field(4.0, many, seed=i)[::-1, ::-1]  # turned half round
        else:
            img = field(4.0, [(x + 0.3 * i, y - 0.2 * i, f) for x, y, f in many], seed=i)  # a slow drift
        h = fits.Header({"DATE-OBS": f"2026-11-15T20:{i:02d}:00", "EXPTIME": 10.0})
        fits.PrimaryHDU(img.astype(np.float32), h).writeto(tmp_path / f"f{i:02d}.fits")
        paths.append(tmp_path / f"f{i:02d}.fits")
    stars = [s[:2] for s in many[:4]]
    lc = light_curve(paths, stars[0], stars[1:], 6, 18, 24)
    assert lc["lost"] == {"f10.fits": ["aligned"]} and len(lc["file"]) == 25
    rel = np.asarray(lc["rel_flux"])
    assert np.allclose(rel, np.median(rel), rtol=0.02)


def test_the_aperture_is_chosen_by_the_steadiest_light_curve(tmp_path):
    """The owner's NY Vir frames: 1.3 FWHM (best for one star's noise) kept 68-80 % of the light, a share that
    differed from star to star and moved with the seeing. With the seeing changing from frame to frame and the target's
    profile a little different from the comparison stars' (focus across the field, colour), a small aperture makes
    the ratio follow the seeing; the scan of radii on pairs of frames picks a large one."""
    from astrowb.photometry.lightcurve import aperture_scan

    target, comps = [(100.0, 100.0, 3e5)], [(60.0, 150.0, 4e5), (150.0, 60.0, 3e5), (45.0, 45.0, 2e5)]
    paths = []
    for i in range(12):
        fwhm = 2.6 if i % 2 else 4.4  # the seeing jumps between frames
        img = field(fwhm, target, seed=i) + field(fwhm, comps, beta=2.5, seed=100 + i) - 300.0
        h = fits.Header({"DATE-OBS": f"2026-11-15T20:{i:02d}:00", "EXPTIME": 10.0})
        fits.PrimaryHDU(img.astype(np.float32), h).writeto(tmp_path / f"f{i:02d}.fits")
        paths.append(tmp_path / f"f{i:02d}.fits")
    stars = [s[:2] for s in target + comps]
    scan = aperture_scan(paths, stars, 3.5, gain=1.0)
    scatter = dict(zip(scan["radii"], scan["scatter"], strict=True))
    assert scatter[3.5] > 3 * scatter[3.5 * 3.0]  # 1 FWHM follows the seeing, 3 FWHM does not
    assert scan["best"] >= 2.0 * 3.5 and scan["r_in"] >= scan["radii"][-1] + 2.0


def test_grouped_median_of_integer_data():
    """plans/photometry.md item 1: integer ADU (raw 8-16 bit frames) gave a sky median rounded to a whole number;
    the median is now taken inside its unit bin, as for grouped data, and float data keep the plain median."""
    from astrowb.photometry.aperture import _grouped_median

    rng = np.random.default_rng(3)
    true = 354.3
    vals = np.round(rng.normal(true, 10, 200_000))
    assert abs(np.median(vals) - true) > 0.25  # the plain median is a whole number
    assert abs(_grouped_median(vals) - true) < 0.05
    floats = rng.normal(true, 10, 1001)
    assert _grouped_median(floats) == np.median(floats)


def test_astroimagej_radii():
    """plans/photometry.md item 1: AstroImageJ's rule, so a night can be measured with the same apertures in both
    programs: the aperture to 1 % of the peak (a Gaussian: 3.03 sigma = 1.29 FWHM, rounded up to a whole pixel), the
    sky ring from 2 to 4 times it; 1.7 / 3.4 / 6.8 FWHM when the profile never gets that low."""
    from astrowb.photometry.aperture import aij_radii

    fwhm = 4.0
    a = choose_apertures(field(fwhm, stars=[(100.0, 100.0, 1e6)]), [(100.0, 100.0)], rule="aij")
    assert a["r_ap"] == np.ceil(1.29 * fwhm) or a["r_ap"] == np.ceil(1.29 * fwhm) + 1  # 0.5 px profile bins
    assert (a["r_in"], a["r_out"]) == (2 * a["r_ap"], 4 * a["r_ap"])
    centres = np.arange(0.25, 20, 0.5)
    flat = np.exp(-centres / 30.0)  # never falls to 1 % inside the profile
    assert aij_radii(centres, flat, 5.0) == (8.0, 17.0, 34.0)


def test_camera_noise_model_predicts_the_scatter():
    """plans/photometry.md item 2: with the camera's gain, read noise and dark current the predicted flux error matches
    the scatter of 1000 noise realisations within 5 % (AstroImageJ's model, Collins et al. 2017 appendix B)."""
    from astrowb.photometry.aperture import measure

    gain, read_noise, dark_rate, exptime, sky = 2.0, 8.0, 0.5, 60.0, 400.0
    dark = dark_rate * exptime  # electrons per pixel over the exposure
    rng = np.random.default_rng(7)
    yy, xx = np.mgrid[:41, :41]
    star = 4e4 / (2 * np.pi * 1.8**2) * np.exp(-((xx - 20.3) ** 2 + (yy - 19.6) ** 2) / (2 * 1.8**2))  # electrons
    fluxes, errs = [], []
    for _ in range(1000):
        e = rng.poisson(star + sky * gain + dark) - dark + rng.normal(0, read_noise, star.shape)
        adu = np.round(e / gain)  # the dark was subtracted (a calibrated frame); its noise stays
        f, err, _ = measure(adu, [(20.3, 19.6)], 5.0, 10.0, 16.0, gain, camera=(read_noise, dark))
        fluxes.append(f[0])
        errs.append(err[0])
    assert np.median(errs) == pytest.approx(np.std(fluxes), rel=0.05)


def test_sky_estimates_with_a_gradient_and_a_star_in_the_ring():
    """plans/photometry.md item 3: a sky gradient (moonlight) and a bright star in the sky ring: the plane fit gives
    the true sky at the target within 0.1 sigma; the others are off (the gradient widens and skews what the clipping
    keeps, and the star's wings stay in)."""
    from astrowb.photometry.aperture import measure

    rng = np.random.default_rng(11)
    yy, xx = np.mgrid[:101, :101]
    x0, y0, sigma = 50.3, 49.7, 5.0
    sky = 500.0 + 0.8 * (xx - x0) - 0.5 * (yy - y0)  # true sky at the target: 500
    img = sky + rng.normal(0, sigma, sky.shape)
    img += 3e4 / (2 * np.pi * 2.0**2) * np.exp(-((xx - x0) ** 2 + (yy - y0) ** 2) / 8.0)
    img += 2e5 / (2 * np.pi * 2.0**2) * np.exp(-((xx - x0 - 13) ** 2 + (yy - y0) ** 2) / 8.0)  # in the ring
    got = {}
    for method in ("median", "mode", "mean", "plane"):
        _, err, s = measure(img, [(x0, y0)], 5.0, 10.0, 18.0, 1.0, sky_method=method)
        got[method] = float(np.ravel(s)[0])
        assert np.isfinite(np.ravel(err)[0])
    assert abs(got["plane"] - 500.0) < 0.1 * sigma
    for method in ("median", "mode", "mean"):
        assert abs(got[method] - 500.0) > 2 * abs(got["plane"] - 500.0), got


def test_light_curve_with_the_other_sky_estimates(tmp_path):
    """plans/photometry.md items 2 and 3 through the whole light curve: every sky estimate and the camera noise model
    give the same relative flux of a flat field within its errors."""
    paths = []
    for i in range(3):
        h = fits.Header({"DATE-OBS": f"2026-11-15T20:{i:02d}:00", "EXPTIME": 10.0})
        fits.PrimaryHDU(field(4.0, seed=i).astype(np.float32), h).writeto(tmp_path / f"f{i}.fits")
        paths.append(tmp_path / f"f{i}.fits")
    stars = [s[:2] for s in STARS]
    ref = light_curve(paths, stars[0], stars[1:], 6, 18, 24)
    for method in ("mode", "mean", "plane"):
        lc = light_curve(paths, stars[0], stars[1:], 6, 18, 24, sky_method=method, camera={"read_noise": 8.0})
        d = np.asarray(lc["rel_flux"]) - np.asarray(ref["rel_flux"])
        assert np.all(np.abs(d) < 3 * np.asarray(ref["rel_flux_err"])), method

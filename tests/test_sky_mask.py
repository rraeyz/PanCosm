"""PHO-45: IRAF's histogram-centroid sky."""

import numpy as np
import pytest

from astrowb.photometry.aperture import sky_estimate


def test_histogram_centroid_finds_the_sky_under_a_star_wing():
    rng = np.random.default_rng(5)
    sigma = 5.0
    v = rng.normal(500.0, sigma, 2000)
    v[:150] += rng.uniform(10, 200, 150)  # a neighbour's wing in 7 % of the ring
    dx = dy = np.zeros(v.size)
    sky, sd, n = sky_estimate(v, dx, dy, "centroid")
    assert sky == pytest.approx(500.0, abs=0.2 * sigma)
    assert v.mean() - 500.0 > 1.5 * sigma  # the plain mean is pulled up
    assert sd == pytest.approx(sigma, rel=0.15) and 1700 < n < 2000


def test_histogram_centroid_of_a_constant_ring():
    assert sky_estimate(np.full(50, 7.0), np.zeros(50), np.zeros(50), "centroid")[:2] == (7.0, 0.0)


def test_a_star_masked_out_of_the_ring():
    """A neighbour in the ring: clipping keeps its faint wings and biases the median up (on average over 20 noise
    draws); masked by position, the bias is a quarter of that and under 0.05 sigma."""
    from astrowb.photometry.aperture import measure, star_mask

    yy, xx = np.mgrid[:101, :101]
    x0, y0, sigma = 50.2, 49.8, 5.0
    stars = 2e5 / (8 * np.pi) * np.exp(-((xx - x0) ** 2 + (yy - y0) ** 2) / 8)
    stars += 1e5 / (18 * np.pi) * np.exp(-((xx - x0 - 14) ** 2 + (yy - y0 - 3) ** 2) / 18)
    mask = star_mask(xx.shape, [(x0 + 14, y0 + 3)], 15)
    plain, masked = [], []
    for seed in range(20):
        img = 300.0 + np.random.default_rng(seed).normal(0, sigma, xx.shape) + stars
        plain.append(float(np.ravel(measure(img, [(x0, y0)], 5, 10, 20)[2])[0]) - 300)
        masked.append(float(np.ravel(measure(img, [(x0, y0)], 5, 10, 20, sky_mask=mask)[2])[0]) - 300)
    assert np.mean(plain) > 4 * np.mean(masked) and np.mean(masked) < 0.05 * sigma


def _ring_frames(tmp_path, n=3, sigma=5.0, shift=(0.0, 0.0)):
    """Frames with a bright target (G 12), two comparison stars and a star 5 mag fainter (G 17) at 13 px from the
    target (inside its sky ring), noise sigma; returns paths, the stars, the catalogue (pixels of frame 0, G)."""
    from astropy.io import fits

    yy, xx = np.mgrid[:200, :200]
    stars = [(100.3, 99.6), (50.2, 150.7), (150.4, 50.3)]
    faint = (113.3, 99.6)
    cat = {
        "x": [*(s[0] for s in stars), faint[0]],
        "y": [*(s[1] for s in stars), faint[1]],
        "gmag": [12.0, 12.0, 12.0, 17.0],
    }
    paths = []
    for i in range(n):
        d = (i * shift[0], i * shift[1])
        img = 300.0 + np.random.default_rng(i).normal(0, sigma, yy.shape)
        for (x, y), flux in [*zip(stars, (2e5, 2e5, 2e5), strict=True), (faint, 2e5 * 10 ** (-0.4 * 5))]:
            img += flux / (2 * np.pi * 2.5**2) * np.exp(-((xx - x - d[0]) ** 2 + (yy - y - d[1]) ** 2) / (2 * 2.5**2))
        h = fits.Header({"DATE-OBS": f"2026-11-28T20:{i:02d}:00", "EXPTIME": 30.0})
        fits.PrimaryHDU(img.astype(np.float32), h).writeto(tmp_path / f"s{i}.fits")
        paths.append(tmp_path / f"s{i}.fits")
    return paths, stars, cat


def test_catalogue_star_in_the_ring_masked_and_counted(tmp_path):
    """A star 5 mag fainter than the target inside its ring, given as a catalogue entry: measured on 30 noise draws,
    the unmasked sky median is biased high (measured: +0.091 sigma over 30 frames), the masked one is within 0.1
    sigma of 300 (measured: +0.019 sigma; the plan's "> 0.5 sigma" holds only for broad halos); the rejected
    count is exactly the masked ring pixels plus those the 3-sigma clip then drops."""
    from astrowb.photometry import skymask
    from astrowb.photometry.aperture import measure
    from astrowb.photometry.lightcurve import light_curve

    sigma = 5.0
    paths, stars, cat = _ring_frames(tmp_path, n=30, sigma=sigma)
    args = (paths, stars[0], stars[1:], 4, 10, 20)
    plain = light_curve(*args, centring="none", sky_method="median")
    masked = light_curve(*args, centring="none", sky_method="median", catalogue_sky=cat)
    bias_plain = np.mean(np.asarray(plain["sky"])[:, 0]) - 300.0
    bias_masked = np.mean(np.asarray(masked["sky"])[:, 0]) - 300.0
    assert abs(bias_masked) < 0.1 * sigma
    assert bias_plain > 0.08 * sigma and bias_plain > 2 * abs(bias_masked)
    assert "sky_rejected" not in plain
    assert np.asarray(masked["sky_rejected"]).shape == (30, 3)
    # independent count on frame 0: the catalogue star's disc (radius 1.5 FWHM, FWHM from the frame) in the ring
    from astropy.io import fits

    img = fits.getdata(paths[0]).astype(float)
    su = skymask.setup(cat, np.array(stars))
    assert len(su["xy"]) == 1 and su["g0"] == 12.0  # the three measured stars are not masked as catalogue stars
    r = masked["radii"][0]
    m = skymask.mask(img.shape, su, np.array(masked["xy"][0]), masked["fwhm"][0] if "fwhm" in masked else 5.9, r[2])
    yy, xx = np.mgrid[:200, :200]
    ring = (np.hypot(xx - masked["xy"][0][0][0], yy - masked["xy"][0][0][1]) >= r[1]) & (
        np.hypot(xx - masked["xy"][0][0][0], yy - masked["xy"][0][0][1]) < r[2]
    )
    from astropy.stats import sigma_clip

    kept = img[ring & ~m]
    expect = int((ring & m).sum() + sigma_clip(kept, sigma=3.0, maxiters=10).mask.sum())
    got = skymask.rejected(img, np.array(masked["xy"][0][:1]), r[1], r[2], m)
    assert got == [expect] and expect >= int((ring & m).sum()) > 100
    assert measure(img, masked["xy"][0][:1], *r, sky_mask=m)[2][0] == pytest.approx(masked["sky"][0][0], abs=0.3)


def test_radius_grows_with_brightness_and_is_capped():
    from astrowb.photometry import skymask

    su = {"g": np.array([17.0, 12.0, 9.0, 0.0]), "g0": 12.0}
    r = skymask.radii(su, 3.0, 40.0)
    assert r[:2] == pytest.approx([4.5, 4.5])  # not brighter than the target: 1.5 FWHM
    assert r[2] == pytest.approx(4.5 * 10**0.6)  # 3 mag brighter
    assert r[3] == 40.0  # capped at the ring's outer radius


def test_catalogue_setup_needs_a_star_on_the_target_and_stops_at_seven_mag():
    from astrowb.photometry import skymask

    cat = {"x": [10.0, 30.0, 40.0], "y": [10.0, 10.0, 10.0], "gmag": [12.0, 18.9, 19.1]}
    su = skymask.setup(cat, np.array([[10.2, 9.9], [90.0, 90.0]]))
    assert su["xy"].tolist() == [[30.0, 10.0]]  # the target itself and G >= 19 are out
    assert skymask.setup(cat, np.array([[60.0, 60.0]])) is None  # no Gaia star on the target: nothing guessed
    assert skymask.setup(None, np.array([[10.0, 10.0]])) is None


def test_the_table_has_the_rejected_counts(tmp_path):
    from astrowb.photometry.lightcurve import light_curve
    from astrowb.photometry.measurements import measurements

    paths, stars, cat = _ring_frames(tmp_path, n=2)
    lc = light_curve(paths, stars[0], stars[1:], 4, 10, 20, centring="none", catalogue_sky=cat)
    cols, _ = measurements(lc)
    assert [isinstance(v, int) for v in cols["Sky_Rejected_T1"]] == [True, True] and "Sky_Rejected_C3" in cols
    cols, _ = measurements(light_curve(paths, stars[0], stars[1:], 4, 10, 20, centring="none"))
    assert "Sky_Rejected_T1" not in cols


def test_the_catalogue_mask_without_catalogue_stars_is_refused(tmp_path):
    import numpy as np
    from astropy.io import fits

    from astrowb.engine.steps import execute

    path = tmp_path / "f.fits"
    fits.PrimaryHDU(np.full((40, 40), 100.0, np.float32)).writeto(path)

    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    import pytest

    with pytest.raises(ValueError, match="catalogue sky mask"):
        execute("photometry.light_curve", {"images": [str(path)], "target_xy": [20, 20], "comps_xy": [[10, 10]]},
                {"sky_mask_catalogue": True}, Ctx())  # fmt: skip

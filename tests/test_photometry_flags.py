"""PHO-36 (without mask planes): a hot pixel or cosmic ray inside an aperture is flagged on exactly its frames; a
star's own core is not; the flags travel in the light curve and its file."""

import numpy as np
from astropy.io import fits
from test_apertures import STARS, field

from astrowb.photometry import lcfile
from astrowb.photometry.flags import aperture_flags
from astrowb.photometry.lightcurve import light_curve


def test_spikes_flagged_on_their_frames_only(tmp_path):
    paths = []
    for i in range(6):
        img = field(4.0, seed=30 + i)
        if i in (2, 3):  # a cosmic ray 2 px from the target's centre
            img[int(STARS[0][1]) + 2, int(STARS[0][0]) - 1] += 3000.0
        h = fits.Header({"DATE-OBS": f"2026-11-15T20:{i:02d}:00", "EXPTIME": 30.0})
        fits.PrimaryHDU(img.astype(np.float32), h).writeto(tmp_path / f"f{i}.fits")
        paths.append(tmp_path / f"f{i}.fits")
    xy = [s[:2] for s in STARS]
    lc = light_curve(paths, xy[0], xy[1:3], 6, 15, 20)
    assert [row[0] for row in lc["flags"]] == ["", "", "C", "C", "", ""]
    assert all(f == "" for row in lc["flags"] for f in row[1:])  # the comparison stars' cores are not spikes
    from astrowb.photometry.measurements import measurements

    cols, marks = measurements(lc)
    assert cols["Flags_T1"] == ["", "", "C", "C", "", ""] and marks[(2, "Flags_T1")] == "cosmic ray or hot pixel"
    from astrowb.photometry.quality import lc_checks

    flags, verdict = lc_checks(lc)  # the Checks tab lists them and "Leave out the flagged points" takes them
    assert flags["spike"] == [2, 3] and verdict.startswith("2 frames with a spike in an aperture")
    back = lcfile.read(lcfile.write(lc, tmp_path / "n.lc.ecsv"))
    assert back["flags"] == lc["flags"]


def test_edge_and_undersampled_core():
    yy, xx = np.mgrid[:40, :40]
    img = 100 + 5e4 / (2 * np.pi * 0.64**2) * np.exp(-((xx - 20.2) ** 2 + (yy - 19.7) ** 2) / (2 * 0.64**2))
    img += np.random.default_rng(1).normal(0, 3, img.shape)
    assert aperture_flags(img, [(20.2, 19.7), (2.0, 20.0)], 4.0) == ["", "E"]  # FWHM 1.5 px: a core, not a spike


def test_no_false_spikes_on_clean_stars():
    xy = [s[:2] for s in STARS]
    for fwhm in (1.8, 2.8, 4.7, 7.0):
        for seed in range(5):
            assert aperture_flags(field(fwhm, seed=seed), xy, 2.5 * fwhm) == [""] * len(xy), (fwhm, seed)
    for seed in range(3):  # Moffat wings too
        assert aperture_flags(field(4.0, beta=2.5, seed=seed), xy, 8.0) == [""] * len(xy)


def test_elongated_core_is_not_a_spike():
    """A star of the owner's T100 night, elongated (from its peak 58 % down on one side, 11 % on the other), was
    flagged as a cosmic ray against the mean of its four neighbours; a real single-pixel spike still is."""
    yy, xx = np.mgrid[:40, :40]
    for cx, cy in ((20.0, 20.0), (20.3, 19.6), (19.5, 20.5)):
        for sx, sy in ((0.9, 2.0), (2.2, 1.0), (1.2, 1.6)):
            r2 = (xx - cx) ** 2 / (2 * sx**2) + (yy - cy) ** 2 / (2 * sy**2)
            img = 500 + 4e5 / (2 * np.pi * sx * sy) * np.exp(-r2)
            img = np.random.default_rng(2).poisson(img).astype(float)
            assert aperture_flags(img, [(cx, cy)], 5.0) == [""], (cx, cy, sx, sy)
            img[int(cy) - 3, int(cx) + 2] += 8000.0  # a cosmic ray in the same aperture
            assert aperture_flags(img, [(cx, cy)], 5.0) == ["C"], (cx, cy, sx, sy)


def test_ellipticity_round_and_elongated():
    from astrowb.photometry.flags import ellipticity

    yy, xx = np.mgrid[:60, :60]
    rng = np.random.default_rng(1)

    def star(sx, sy):
        return 1000 * np.exp(-((xx - 30) ** 2 / sx**2 + (yy - 30) ** 2 / sy**2) / 2) + 50 + rng.normal(0, 2, xx.shape)

    assert ellipticity(star(2, 2), [[30, 30]], 10) < 0.05
    assert abs(ellipticity(star(1.5, 3), [[30, 30]], 10) - 0.5) < 0.05
    assert ellipticity(star(2, 2), [[np.nan, 5]], 10) is None

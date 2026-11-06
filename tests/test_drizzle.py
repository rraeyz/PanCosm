"""Drizzle on undersampled, dithered frames of a known star field."""

import numpy as np
import pytest

from astrowb.calibration.drizzle import drizzle, scaled_header


def star_frame(dx, dy, shape=(40, 50), x0=24.3, y0=19.6, sigma=0.55, flux=1e4):
    """Pixel-integrated Gaussian star (sharper than a pixel) seen with the frame shifted by (dx, dy)."""
    from scipy.special import erf

    def edges(n, c):
        e = np.arange(n + 1) - 0.5
        return 0.5 * np.diff(erf((e - c) / (np.sqrt(2) * sigma)))

    return flux * np.outer(edges(shape[0], y0 + dy), edges(shape[1], x0 + dx))


def test_drizzle_keeps_flux_and_position_and_sharpens():
    rng = np.random.default_rng(0)
    offsets = [tuple(v) for v in rng.uniform(-0.5, 0.5, (16, 2))]
    frames = [star_frame(dx, dy) for dx, dy in offsets]
    out, weight = drizzle(frames, offsets, scale=2, pixfrac=0.6)
    assert out.shape == (80, 100) and np.all(weight > 0)
    assert np.nansum(out) == pytest.approx(1e4, rel=0.02)  # counts kept (Fruchter & Hook's s^2 factor)
    yy, xx = np.mgrid[:80, :100]
    cx, cy = (
        (np.nansum(out * xx) / np.nansum(out) + 0.5) / 2 - 0.5,
        (np.nansum(out * yy) / np.nansum(out) + 0.5) / 2 - 0.5,
    )
    assert cx == pytest.approx(24.3, abs=0.05) and cy == pytest.approx(19.6, abs=0.05)
    plain = np.mean(frames, axis=0)  # stacked without dithers resolved: a blurred star
    assert out.max() * 4 / out.sum() > 1.3 * plain.max() / plain.sum()  # per input-pixel area: x scale^2


def test_scaled_header_keeps_the_sky_position():
    from astropy.io import fits
    from astropy.wcs import WCS

    h = fits.Header(
        {
            "CTYPE1": "RA---TAN",
            "CTYPE2": "DEC--TAN",
            "CRVAL1": 10.0,
            "CRVAL2": 20.0,
            "CRPIX1": 25.0,
            "CRPIX2": 20.0,
            "CD1_1": -0.001,
            "CD1_2": 0.0,
            "CD2_1": 0.0,
            "CD2_2": 0.001,
        }
    )
    a = WCS(h).pixel_to_world(10.0, 7.0)
    b = WCS(scaled_header(h, 2)).pixel_to_world((10.0 + 0.5) * 2 - 0.5, (7.0 + 0.5) * 2 - 0.5)
    assert a.separation(b).arcsec < 1e-6


def test_scaled_header_keeps_the_distortion():
    """A plate-solved frame carries SIP terms; the drizzled grid must give the same sky position at its corners."""
    from astropy.io import fits
    from astropy.wcs import WCS

    h = fits.Header({"CTYPE1": "RA---TAN-SIP", "CTYPE2": "DEC--TAN-SIP", "CRVAL1": 10.0, "CRVAL2": 20.0,
                     "CRPIX1": 1000.0, "CRPIX2": 800.0, "CD1_1": -2e-4, "CD1_2": 1e-6, "CD2_1": -1e-6, "CD2_2": 2e-4,
                     "A_ORDER": 2, "B_ORDER": 2, "A_2_0": 3e-6, "A_1_1": -2e-6, "A_0_2": 1e-6, "B_2_0": -1e-6,
                     "B_1_1": 4e-6, "B_0_2": 2e-6})  # fmt: skip
    a = WCS(h).pixel_to_world(5.0, 1590.0)  # a corner: ~4 px of distortion
    b = WCS(scaled_header(h, 2)).pixel_to_world((5.0 + 0.5) * 2 - 0.5, (1590.0 + 0.5) * 2 - 0.5)
    assert a.separation(b).arcsec < 1e-4


def test_drizzle_step_writes_a_finer_image(tmp_path):
    from astropy.io import fits

    from astrowb.engine.steps import execute

    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    rng = np.random.default_rng(3)
    paths = []
    for i, (dx, dy) in enumerate(rng.uniform(-3, 3, (6, 2))):
        frame = star_frame(dx, dy, x0=24.3, y0=19.6) + star_frame(dx, dy, x0=10.0, y0=30.0, flux=6e3) + 50.0
        h = fits.Header({"DATE-OBS": f"2026-11-15T20:{i:02d}:00", "EXPTIME": 10.0})
        fits.PrimaryHDU(frame.astype(np.float32), h).writeto(tmp_path / f"f{i}.fits")
        paths.append(str(tmp_path / f"f{i}.fits"))
    out = execute("stacking.drizzle", {"images": paths, "output": str(tmp_path / "d.fits")}, {}, Ctx())["stack"]
    with fits.open(out) as hdul:
        assert hdul[0].data.shape == (80, 100) and hdul["WEIGHT"].data.max() > 0 and hdul[0].header["NCOMBINE"] == 6

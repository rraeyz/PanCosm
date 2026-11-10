"""IMG-14: a cut-out around a star keeps the star at its sky position; a frame turned 30° comes out north-up with the
star where its coordinates say and its flux kept."""

import numpy as np
from astropy.wcs import WCS

from astrowb.io.cutout import cutout, north_up
from astrowb.photometry.aperture import measure, recenter


def turned_frame():
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval, w.wcs.crpix = [204.70, -2.03], [101, 81]
    a, s = np.radians(30), 1.5 / 3600
    w.wcs.cd = s * np.array([[-np.cos(a), np.sin(a)], [np.sin(a), np.cos(a)]])
    shape = (160, 200)
    yy, xx = np.indices(shape)
    x0, y0 = 140.3, 50.6
    img = 100 + 5e4 / (2 * np.pi * 2.0**2) * np.exp(-((xx - x0) ** 2 + (yy - y0) ** 2) / (2 * 2.0**2))
    return img, w, w.pixel_to_world_values(x0, y0)


def test_cutout_and_north_up():
    img, w, (ra, dec) = turned_frame()
    part, pw = cutout(img, w, (ra, dec), 1.0)
    px, py = pw.world_to_pixel_values(ra, dec)
    cx, cy = recenter(np.nan_to_num(part, nan=100.0), [(px, py)], 7)[0]
    assert np.hypot(cx - px, cy - py) < 0.1 and part.shape == (40, 40)  # 1′ at 1.5″ per pixel
    up, uw = north_up(img, w)
    assert uw.wcs.cd[0, 0] < 0 and uw.wcs.cd[1, 1] > 0 and abs(uw.wcs.cd[0, 1]) < 1e-12  # north up, east left
    qx, qy = uw.world_to_pixel_values(ra, dec)
    fx, fy = recenter(np.nan_to_num(up, nan=100.0), [(qx, qy)], 7)[0]
    assert np.hypot(fx - qx, fy - qy) < 0.15
    flux = measure(np.nan_to_num(up, nan=100.0), [(fx, fy)], 8, 12, 16)[0][0]
    assert abs(flux / 5e4 - 1) < 0.01  # the same scale: the counts kept

"""PHO-24: two stars measured against each other — separation, position angle, flux ratio, Δmag."""

import numpy as np
import pytest
from astropy.wcs import WCS

from astrowb.io.inspect import pair_measure


def pair_image():
    ny, nx = 200, 220
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval, w.wcs.crpix = [150.0, 20.0], [nx / 2, ny / 2]
    w.wcs.cd = np.array([[-1.0, 0.0], [0.0, 1.0]]) / 3600  # 1"/px, north up, east left
    x1, y1 = 95.3, 88.7
    pa, sep = np.radians(123.0), 37.5
    x2, y2 = x1 - sep * np.sin(pa), y1 + sep * np.cos(pa)  # east is towards −x
    yy, xx = np.mgrid[:ny, :nx]
    img = np.full((ny, nx), 300.0)
    total1 = 2e6
    for x, y, f in ((x1, y1, total1), (x2, y2, 0.25 * total1)):
        img += f / (2 * np.pi * 1.8**2) * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 1.8**2))
    img += np.random.default_rng(2).normal(0, 3, img.shape)
    return img, w, (x1, y1), (x2, y2), sep


def test_a_pair_at_37_5_px_and_123_degrees():
    img, w, (x1, y1), (x2, y2), sep = pair_image()
    out = pair_measure(img, (x1 + 1.2, y1 - 0.8), (x2 - 0.9, y2 + 1.1), wcs=w, r_ap=8, r_in=12, r_out=17)
    assert out["ratio"] == pytest.approx(0.25, rel=0.005)
    assert out["separation_px"] == pytest.approx(sep, abs=0.02)
    assert out["position_angle"] == pytest.approx(123.0, abs=0.05)
    assert out["separation_arcsec"] == pytest.approx(sep, rel=1e-3)
    assert out["dmag"] == pytest.approx(2.5 * np.log10(4), abs=0.006) and 0 < out["dmag_err"] < 0.01


def test_the_line_tool_measures_the_pair_only_on_stars(qapp):
    from astrowb.ui.image_pair import pair_rows

    img, w, (x1, y1), (x2, y2), _ = pair_image()
    rows = dict(pair_rows(img, x1 + 1, y1, x2, y2 - 1, w))
    assert rows["Pair: position angle (°, N through E)"].startswith("123.0")
    assert pair_rows(img, x1, y1, 20.0, 180.0, w) == []  # one end on empty sky: the line alone

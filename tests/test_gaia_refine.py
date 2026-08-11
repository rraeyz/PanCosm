"""Plate solution refined on catalogue stars (Gaia DR3 in use; the catalogue is given here, no network)."""

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from astrowb import gaia


def _field(seed=3, n=120, shape=(400, 500)):
    rng = np.random.default_rng(seed)
    true = WCS(naxis=2)
    true.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    true.wcs.crval = [200.4, -18.65]
    true.wcs.crpix = [250.5, 200.5]
    true.wcs.cd = np.array([[-2.05e-4, 1.0e-6], [1.0e-6, 2.05e-4]])  # 0.74"/px
    x, y = rng.uniform(15, shape[1] - 15, n), rng.uniform(15, shape[0] - 15, n)
    flux = rng.uniform(3e3, 6e4, n)
    yy, xx = np.mgrid[: shape[0], : shape[1]]
    img = rng.normal(300, 8, shape)
    for xi, yi, f in zip(x, y, flux, strict=True):
        img += f / (2 * np.pi * 1.6**2) * np.exp(-((xx - xi) ** 2 + (yy - yi) ** 2) / (2 * 1.6**2))
    ra, dec = true.pixel_to_world_values(x, y)
    pm = rng.normal(0, 8, (2, n))  # mas/yr
    year = 2026.6
    cat = {  # catalogue positions at J2016.0: moved back by the proper motions
        "ra": ra - pm[0] * (year - 2016) / 3.6e6 / np.cos(np.radians(dec)),
        "dec": dec - pm[1] * (year - 2016) / 3.6e6,
        "pmra": pm[0],
        "pmdec": pm[1],
        "gmag": 20 - 2.5 * np.log10(flux),
    }
    return img.astype(np.float32), true, cat, year


def test_a_shifted_and_turned_solution_is_brought_onto_the_catalogue():
    img, true, cat, year = _field()
    off = true.deepcopy()
    off.wcs.crval = off.wcs.crval + [1.5 / 3600, -1.2 / 3600]  # 1.9" off
    a = np.radians(0.05)
    off.wcs.cd = off.wcs.cd @ np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])  # turned 0.05 deg
    header = fits.Header({"DATE-OBS": "2026-08-08T03:00:00", "EXPTIME": 120.0}) + off.to_header()
    new, info = gaia.refine_wcs(img, header, cat=cat, year=year)
    assert info["matched"] >= 60 and info["rms_before"] > 1.0 and info["rms_after"] < 0.1
    w = WCS(new)
    xs, ys = np.meshgrid([20, 250, 480], [20, 200, 380])
    sep = w.pixel_to_world(xs.ravel(), ys.ravel()).separation(true.pixel_to_world(xs.ravel(), ys.ravel())).arcsec
    assert sep.max() < 0.1 and new["ASTCAT"] == "Gaia3"


def test_too_few_matching_stars_is_said():
    img, true, cat, year = _field(n=5)
    header = fits.Header({"DATE-OBS": "2026-08-08T03:00:00"}) + true.to_header()
    try:
        gaia.refine_wcs(img, header, cat=cat, year=year)
    except ValueError as e:
        assert "too few" in str(e)
    else:
        raise AssertionError("five stars cannot refine a solution")


def test_a_cone_inside_one_fetched_is_not_fetched_again(monkeypatch):
    calls = []

    def fake(ra, dec, radius, mag, rows):
        calls.append(radius)
        n = 50
        rng = np.random.default_rng(1)
        return {"ra": ra + rng.uniform(-radius, radius, n), "dec": dec + rng.uniform(-radius, radius, n),
                "pmra": np.zeros(n), "pmdec": np.zeros(n), "gmag": rng.uniform(10, 16, n)}  # fmt: skip

    monkeypatch.setattr(gaia, "_CACHE", [])
    monkeypatch.setattr(gaia, "_vizier", lambda *a: None)
    monkeypatch.setattr(gaia, "_esa", fake)
    a = gaia.stars(200.40, -18.65, 0.30, 17)
    b = gaia.stars(200.43, -18.64, 0.30, 15)  # the next frame, dithered: inside the cone fetched (x 1.3)
    assert len(calls) == 1 and len(b["ra"]) <= len(a["ra"]) and (b["gmag"] < 15).all()
    gaia.stars(201.5, -18.65, 0.30, 17)  # another field
    assert len(calls) == 2

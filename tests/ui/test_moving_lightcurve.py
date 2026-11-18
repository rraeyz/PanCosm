"""PHO-21: the Astrometry window's Light curve stage: a moving star of constant brightness among field stars gives a
flat curve within its errors, and the ALCDEF file is written with DATA lines."""

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS

from astrowb.settings import Settings
from astrowb.ui import moving_lightcurve as lc
from astrowb.ui.moving_dialog import MovingObjectPage

SHAPE, SIGMA, N = (200, 300), 1.6, 8


def star(img, x, y, flux):
    yy, xx = np.indices(img.shape)
    sl = (slice(max(0, int(y) - 10), int(y) + 11), slice(max(0, int(x) - 10), int(x) + 11))
    img[sl] += flux / (2 * np.pi * SIGMA**2) * np.exp(-((xx[sl] - x) ** 2 + (yy[sl] - y) ** 2) / (2 * SIGMA**2))


def frames(tmp_path):
    rng = np.random.default_rng(4)
    stars = np.column_stack([rng.uniform(25, 275, 40), rng.uniform(25, 175, 40)])
    stars = stars[np.hypot(stars[:, 0] - 150, stars[:, 1] - 100) > 80]  # clear of the object's track
    w = WCS(naxis=2)
    w.wcs.ctype, w.wcs.crval, w.wcs.crpix, w.wcs.cdelt = (
        ["RA---TAN", "DEC--TAN"],
        [150.0, 20.0],
        [150, 100],
        [-3e-4, 3e-4],
    )
    paths, track = [], []
    for k in range(N):
        pos = (60.0 + 25.0 * k, 100.0 + 2.0 * k)
        img = np.full(SHAPE, 300.0)
        for x, y in stars:
            star(img, x, y, 20000.0)
        star(img, *pos, 8000.0)
        header = w.to_header()
        header["DATE-OBS"], header["EXPTIME"] = f"2026-11-15T21:{10 + 3 * k:02d}:00", 30.0
        p = tmp_path / f"f{k}.fits"
        fits.PrimaryHDU(rng.poisson(img).astype(np.float32), header).writeto(p)
        paths.append(str(p))
        track.append(pos)
    return paths, track


@pytest.fixture
def page(qtbot, tmp_path):
    p = MovingObjectPage(Settings(tmp_path))
    qtbot.addWidget(p)
    return p


def test_flat_curve_and_alcdef_file(qtbot, tmp_path, page):
    paths, track = frames(tmp_path)
    page.set_images(paths)
    page.first, page.last = track[0], track[-1]  # no Measure stage: the two marks give the track
    page.lc_button.click()
    qtbot.waitUntil(lambda: bool(page.lc_rows), timeout=60000)
    rows = [r for r in page.lc_rows if not r["blended"]]
    mag, err = np.array([r["mag"] for r in rows]), np.array([r["err"] for r in rows])
    assert len(rows) >= N - 1 and np.std(mag, ddof=1) < 1.5 * err.mean()
    assert page.lc_table.table.rowCount() == N and page.lc_save.isEnabled()
    out = tmp_path / "a.txt"
    keys = {"object_number": 0, "object_name": "Test", "filter": "C", "magband": "R", "contact_name": "A",
            "contact_info": "a@b.c", "observers": "A"}  # fmt: skip
    assert lc.export(page, str(out), keys) == str(out)
    text = out.read_text().splitlines()
    assert sum(t.startswith("DATA=") for t in text) == len(rows) and "STANDARD=INTERNAL" in text


def test_failures_are_said_not_raised(qtbot, tmp_path, page):
    page.lc_button.click()
    assert "Choose the frames" in page.hint.text()
    paths, _ = frames(tmp_path)
    page.set_images(paths)
    page.lc_button.click()  # no positions and no marks
    qtbot.waitUntil(lambda: page.lc_button.isEnabled(), timeout=60000)
    assert "no object positions" in page.hint.text() and not page.lc_save.isEnabled()
    page.lc_rows = [{"jd": 2461000.0 + i, "mag": 15.0, "err": 0.01, "blended": False} for i in range(3)]
    assert lc.export(page, str(tmp_path / "b.txt"), {"object_number": 0, "object_name": ""}) is None
    assert "OBJECTNAME" in page.hint.text()

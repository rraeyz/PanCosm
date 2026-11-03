"""Live light curve: incremental frames give the same result as the batch light curve."""

import os

import numpy as np
from astropy.io import fits

from astrowb.photometry import live
from astrowb.photometry.lightcurve import light_curve

STARS = [(30, 20, 20000.0), (55, 40, 15000.0), (15, 45, 12000.0)]


def write_frames(folder, n=20, flat=None):
    rng = np.random.default_rng(2)
    y, x = np.mgrid[:60, :80]
    paths = []
    for i in range(n):
        dx, dy = 0.3 * i, -0.2 * i
        img = rng.normal(100, 3, (60, 80))
        for k, (sx, sy, f) in enumerate(STARS):
            f = f * (0.97 if (k == 0 and 8 <= i < 14) else 1.0)
            img += f / (2 * np.pi * 1.5**2) * np.exp(-((x - sx - dx) ** 2 + (y - sy - dy) ** 2) / (2 * 1.5**2))
        if flat is not None:
            img = img * flat
        h = fits.Header({"DATE-OBS": f"2026-10-01T20:{i:02d}:00", "EXPTIME": 30.0, "GAIN": 2.0, "IMAGETYP": "Light"})
        p = folder / f"f{i:02d}.fits"
        fits.PrimaryHDU(img.astype(np.float32), h).writeto(p)
        os.utime(p, (1000 + i, 1000 + i))  # file times in acquisition order
        paths.append(str(p))
    return paths


def test_ready_files_waits_for_writing_and_skips_seen(tmp_path):
    paths = write_frames(tmp_path, 3)
    assert live.ready_files(tmp_path, set(), now=1002.5) == paths[:1]  # the other two are "still being written"
    assert live.ready_files(tmp_path, {paths[0]}, now=1010) == paths[1:]


def test_live_matches_batch_and_uses_masters(tmp_path):
    y, x = np.mgrid[:60, :80]
    flat = (1 - 0.15 * ((x - 40) ** 2 + (y - 30) ** 2) / 2500).astype(np.float32)  # vignetting
    paths = write_frames(tmp_path, flat=flat)
    flat_path = tmp_path / "master_flat.fits"
    fits.PrimaryHDU(flat, fits.Header({"IMAGETYP": "Flat Field"})).writeto(flat_path)
    masters = live.load_masters([flat_path])
    assert set(masters) == {"flat"}
    session = live.LiveLightCurve(
        STARS[0][:2], [s[:2] for s in STARS[1:]], 4, 10, 16, "02:04:10 +46:41:16", masters=masters
    )
    seen = set()
    for p in live.ready_files(tmp_path, seen, now=5000):
        if "master" in p:
            continue
        seen.add(p)
        assert session.add(p) is not None
    lc = session.light_curve()
    assert len(lc["rel_flux"]) == 20 and lc["time_scale"] == "BJD_TDB"
    rel = np.array(lc["rel_flux"])
    assert abs(rel[10] / rel[2] - 0.97) < 0.01  # the flat removed the vignetting the stars drift through
    # batch on the same (uncalibrated) frames: identical method, so identical numbers without masters
    raw = live.LiveLightCurve(STARS[0][:2], [s[:2] for s in STARS[1:]], 4, 10, 16, "02:04:10 +46:41:16")
    for p in paths:
        raw.add(p)
    batch = light_curve(paths, STARS[0][:2], [s[:2] for s in STARS[1:]], 4, 10, 16, "02:04:10 +46:41:16")
    assert np.allclose(raw.light_curve()["rel_flux"], batch["rel_flux"], rtol=1e-10)
    assert np.allclose(raw.light_curve()["time"], batch["time"], rtol=0, atol=1e-9)


def test_bad_frame_is_reported_not_fatal(tmp_path):
    paths = write_frames(tmp_path, 3)
    (tmp_path / "broken.fits").write_bytes(b"not a fits file")
    session = live.LiveLightCurve(STARS[0][:2], [s[:2] for s in STARS[1:]], 4, 10, 16)
    assert session.add(paths[0]) is not None
    assert session.add(str(tmp_path / "broken.fits")) is None and "broken.fits" in next(iter(session.failed))
    assert session.add(paths[1]) is not None and len(session.points) == 2

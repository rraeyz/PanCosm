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


def test_ready_files_leaves_a_file_cut_short(tmp_path):
    """PHO-19 item 3: a frame whose header does not read yet (the camera still writing) waits for a later poll."""
    paths = write_frames(tmp_path, 1)
    cut = tmp_path / "cut.fits"
    with open(paths[0], "rb") as f:
        cut.write_bytes(f.read()[:100])
    os.utime(cut, (1000, 1000))
    assert live.ready_files(tmp_path, set(), now=5000) == paths


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


def test_a_frame_without_a_comparison_star_is_measured_against_the_others(tmp_path):
    """PHO-19: as in the night run, a frame where one comparison star is not found is measured against the ones it
    has (the missing star's share from the full frames), and it is named; without any comparison star it is left
    out with why."""
    paths = write_frames(tmp_path, 3)
    data = fits.getdata(paths[2]).astype(float)
    y, x = np.mgrid[:60, :80]
    sx, sy, f = STARS[2]
    data -= f / (2 * np.pi * 1.5**2) * np.exp(-((x - sx - 0.6) ** 2 + (y - sy + 0.4) ** 2) / (2 * 1.5**2))
    fits.PrimaryHDU(data.astype(np.float32), fits.getheader(paths[2])).writeto(paths[2], overwrite=True)
    session = live.LiveLightCurve(STARS[0][:2], [s[:2] for s in STARS[1:]], 4, 10, 16)
    assert session.add(paths[0]) is not None and session.add(paths[1]) is not None
    point = session.add(paths[2])
    assert point is not None and point["missing"] == [2] and not session.failed
    lc = session.light_curve()
    assert lc["partial"] == {"f02.fits": [2]} and abs(lc["rel_flux"][2] / lc["rel_flux"][0] - 1) < 0.01  # no jump
    batch = light_curve(paths, STARS[0][:2], [s[:2] for s in STARS[1:]], 4, 10, 16)
    assert np.allclose(lc["rel_flux"], batch["rel_flux"], rtol=1e-6) and batch["partial"] == lc["partial"]


def test_live_measures_the_check_stars_as_the_night_run(tmp_path):
    """PHO-19: a check star given to the live session is measured against the same comparison stars, as the night
    run's extra stars (the window computes their curves from extra_flux)."""
    paths = write_frames(tmp_path, 6)
    target, comps, check = STARS[0][:2], [STARS[1][:2]], [STARS[2][:2]]
    session = live.LiveLightCurve(target, comps, 4, 10, 16, extra_xy=check)
    for p in paths:
        assert session.add(p) is not None
    lc = session.light_curve()
    batch = light_curve(paths, target, comps, 4, 10, 16, extra_xy=check)
    assert np.allclose(lc["extra_flux"], batch["extra_flux"], rtol=1e-9)
    assert np.allclose(lc["rel_flux"], batch["rel_flux"], rtol=1e-9)


def test_live_uses_the_camera_noise_model_and_the_time_rule(tmp_path):
    """PHO-19: the camera's read noise and dark current and the header-time rule reach the live light curve as they
    reach the night run: the same errors and the same times."""
    paths = write_frames(tmp_path, 4)
    target, comps = STARS[0][:2], [s[:2] for s in STARS[1:]]
    camera = {"read_noise": 12.0, "dark": 0.5}
    session = live.LiveLightCurve(target, comps, 4, 10, 16, camera=camera, header_time="end", shutter_delay=0.2)
    for p in paths:
        session.add(p)
    lc = session.light_curve()
    batch = light_curve(paths, target, comps, 4, 10, 16, camera=camera, header_time="end", shutter_delay=0.2)
    assert np.allclose(lc["rel_flux_err"], batch["rel_flux_err"], rtol=1e-9)
    assert np.allclose(lc["jd_utc"], batch["jd_utc"], rtol=0, atol=1e-9)
    plain = light_curve(paths, target, comps, 4, 10, 16)
    assert not np.allclose(lc["rel_flux_err"], plain["rel_flux_err"], rtol=1e-6)  # the camera made a difference


def test_live_uses_the_aperture_shape_as_the_night_run(tmp_path):
    """PHO-22: an ellipse given to the live session measures a frame as the night run does."""
    paths = write_frames(tmp_path, 4)
    target, comps = STARS[0][:2], [s[:2] for s in STARS[1:]]
    shape = {"kind": "ellipse", "ratio": 0.6, "angle": 30.0}
    session = live.LiveLightCurve(target, comps, 4, 10, 16, aperture_shape=shape)
    for p in paths:
        assert session.add(p) is not None
    lc = session.light_curve()
    batch = light_curve(paths, target, comps, 4, 10, 16, shape=shape)
    assert np.allclose(lc["rel_flux"], batch["rel_flux"], rtol=0, atol=1e-9)
    assert np.allclose(lc["rel_flux_err"], batch["rel_flux_err"], rtol=0, atol=1e-9)

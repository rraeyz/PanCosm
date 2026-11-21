"""CAL-22: a night replayed frame by frame gives the same calibrated data as the batch run, bit for bit."""

from pathlib import Path

import numpy as np
from astropy.io import fits

from astrowb.calibration.live import LiveCalibrator
from astrowb.engine.steps import execute


class Ctx:
    def progress(self, *a):
        pass

    def check(self):
        pass


def test_a_replayed_night_equals_the_batch(tmp_path):
    rng = np.random.default_rng(3)
    raw = tmp_path / "raw"
    raw.mkdir()
    shape = (80, 100)
    for i in range(5):
        fits.PrimaryHDU((300 + rng.normal(0, 3, shape)).astype(np.float32),
                        fits.Header({"IMAGETYP": "BIAS"})).writeto(raw / f"b{i}.fits")  # fmt: skip
        fits.PrimaryHDU((310 + rng.normal(0, 3, shape)).astype(np.float32),
                        fits.Header({"IMAGETYP": "DARK", "EXPTIME": 30.0})).writeto(raw / f"d{i}.fits")  # fmt: skip
        fits.PrimaryHDU((300 + 20000 * (1 + rng.normal(0, 0.01, shape))).astype(np.float32),
                        fits.Header({"IMAGETYP": "FLAT", "EXPTIME": 1.0})).writeto(raw / f"f{i}.fits")  # fmt: skip
    lights = tmp_path / "lights"
    lights.mkdir()
    for i in range(4):
        fits.PrimaryHDU((900 + rng.normal(0, 10, shape)).astype(np.float32),
                        fits.Header({"IMAGETYP": "LIGHT", "EXPTIME": 30.0,
                                     "DATE-OBS": f"2026-11-14T20:0{i}:00"})).writeto(lights / f"l{i}.fits")  # fmt: skip
    scan = execute("calibration.scan", {"folder": str(raw), "lights": str(lights)}, {}, Ctx())
    batch = execute("calibration.run", {"frames": scan["frames"], "output_dir": str(tmp_path / "batch")}, {}, Ctx())
    live = LiveCalibrator(batch["masters"], tmp_path / "live")
    done = live.poll(lights)
    assert len(done) == 4 and live.poll(lights) == []  # the second look finds nothing new
    for path in done:
        ours = fits.getdata(path)
        theirs = fits.getdata(next(p for p in batch["calibrated"] if Path(p).name == Path(path).name))
        assert np.array_equal(ours, theirs)
    assert fits.getheader(done[0])["CALF"].startswith("master_flat")


def _night(tmp_path, write_planes):
    rng = np.random.default_rng(5)
    raw, lights, shape = tmp_path / "raw", tmp_path / "lights", (60, 70)
    raw.mkdir()
    lights.mkdir()
    for i in range(5):
        for kind, level, t, d in (("BIAS", 300, 0.0, raw), ("DARK", 310, 30.0, raw), ("FLAT", 20300, 1.0, raw)):
            fits.PrimaryHDU((level + rng.normal(0, 30, shape)).astype(np.float32),
                            fits.Header({"IMAGETYP": kind, "EXPTIME": t})).writeto(d / f"{kind}{i}.fits")  # fmt: skip
    for i in range(3):
        fits.PrimaryHDU((900 + rng.normal(0, 10, shape)).astype(np.float32),
                        fits.Header({"IMAGETYP": "LIGHT", "EXPTIME": 30.0, "EGAIN": 1.5, "RDNOISE": 5.0,
                                     "DATE-OBS": f"2026-11-14T20:0{i}:00"})).writeto(lights / f"l{i}.fits")  # fmt: skip
    scan = execute("calibration.scan", {"folder": str(raw), "lights": str(lights)}, {}, Ctx())
    params = {"write_planes": write_planes}
    return lights, execute(
        "calibration.run", {"frames": scan["frames"], "output_dir": str(tmp_path / "b")}, params, Ctx()
    )


def test_live_var_plane_counts_the_masters_variance_like_the_batch(tmp_path):
    lights, batch = _night(tmp_path, True)
    for m in batch["masters"]:
        assert "VAR" in [h.name for h in fits.open(m)]
        assert fits.getdata(m).shape == (60, 70)  # still reads as a plain image
    live = LiveCalibrator(batch["masters"], tmp_path / "live")
    for path in live.poll(lights):
        for ext in ("SCI", "VAR"):
            ours = fits.getdata(path, extname=ext).astype(float)
            theirs = fits.getdata(next(p for p in batch["calibrated"] if Path(p).name == Path(path).name), extname=ext)
            np.testing.assert_allclose(ours, theirs, rtol=1e-9)


def test_masters_stay_single_image_when_planes_are_off(tmp_path):
    _, batch = _night(tmp_path, False)
    assert all(len(fits.open(m)) == 1 for m in batch["masters"])


def _night_with(tmp_path, mark):
    rng = np.random.default_rng(9)
    raw, lights, shape = tmp_path / "raw", tmp_path / "lights", (160, 160)
    raw.mkdir()
    lights.mkdir()
    for i in range(5):
        for kind, level, t in (("BIAS", 300, 0.0), ("DARK", 310, 30.0), ("FLAT", 20300, 1.0)):
            fits.PrimaryHDU((level + rng.normal(0, 3, shape)).astype(np.float32),
                            fits.Header({"IMAGETYP": kind, "EXPTIME": t})).writeto(raw / f"{kind}{i}.fits")  # fmt: skip
    img = (900 + rng.normal(0, 10, shape)).astype(np.float32)
    mark(img)
    fits.PrimaryHDU(img, fits.Header({"IMAGETYP": "LIGHT", "EXPTIME": 30.0, "EGAIN": 1.5,
                                      "DATE-OBS": "2026-11-14T20:00:00"})).writeto(lights / "l0.fits")  # fmt: skip
    scan = execute("calibration.scan", {"folder": str(raw), "lights": str(lights)}, {}, Ctx())
    return lights, scan["frames"]


def _same(tmp_path, mark, options, live_kw):
    lights, frames = _night_with(tmp_path, mark)
    batch = execute("calibration.run", {"frames": frames, "output_dir": str(tmp_path / "b")}, options, Ctx())
    live = LiveCalibrator(batch["masters"], tmp_path / "live", **live_kw)
    (path,) = live.poll(lights)
    for ext in ("SCI", "VAR", "DQ"):
        ours, theirs = (fits.getdata(p, extname=ext).astype(float) for p in (path, batch["calibrated"][0]))
        np.testing.assert_allclose(ours, theirs, rtol=1e-9)
    return live, batch, fits.getdata(path, extname="DQ")


def test_live_cosmic_rays_equal_the_batch(tmp_path):
    def spike(img):
        img[80, 80] += 5000

    _, _, dq = _same(tmp_path, spike, {"cosmic_rays": True}, {"cosmic_rays": True})
    assert dq[80, 80] != 0


def test_live_trails_equal_the_batch(tmp_path):
    def line(img):
        for x in range(160):
            img[x, x] += 150

    live, batch, dq = _same(tmp_path, line, {"find_trails": True}, {"params": {"find_trails": True}})
    assert live.trails == batch["trails"] and len(live.trails) == 1 and dq.any()


def test_live_options_off_do_no_extra_work(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("searched")

    monkeypatch.setattr("astrowb.calibration.trails.find", boom)
    monkeypatch.setattr("astrowb.calibration.cosmics.detect_cosmics", boom)
    _same(tmp_path, lambda img: None, {}, {})

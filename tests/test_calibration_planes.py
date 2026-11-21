"""CAL-13: the calibration run writes SCI / VAR / DQ (the variance equals the scatter of repeated frames, a saturated
pixel is flagged), plain FITS when the setting is off, and the readers of the program open both."""

import numpy as np
from astropy.io import fits
from test_apertures import STARS, field

from astrowb.core import planes
from astrowb.engine.steps import execute
from astrowb.io import fits as fitsio
from astrowb.photometry import planes_use
from astrowb.photometry.lightcurve import light_curve

GAIN, RN, BIAS = 2.0, 5.0, 300.0


class Ctx:
    def progress(self, *a):
        pass

    def check(self):
        pass


def _save(path, data, gain=GAIN, **cards):
    h = fits.Header({"FILTER": "V", "RDNOISE": RN, "SATURATE": 60000.0} | ({"EGAIN": gain} if gain else {}) | cards)
    fits.PrimaryHDU(np.asarray(data, np.float32), h).writeto(path)


def _night(folder, lights, gain=GAIN, **params):
    return _run_night(folder, lights, gain, **params)["calibrated"]


def _run_night(folder, lights, gain=GAIN, **params):
    """Bias, flat and the given lights (arrays) written to folder; calibrated into folder/cal."""
    rng = np.random.default_rng(1)
    shape = lights[0].shape
    for i in range(10):
        _save(folder / f"b{i}.fits", BIAS + rng.normal(0, RN / GAIN, shape), gain=gain, IMAGETYP="BIAS", EXPTIME=0.0)
    for i in range(5):
        _save(folder / f"f{i}.fits", BIAS + 20000 + rng.normal(0, 40, shape), gain=gain, IMAGETYP="FLAT", EXPTIME=2.0)
    for i, a in enumerate(lights):
        _save(
            folder / f"l{i:02d}.fits",
            a,
            gain=gain,
            IMAGETYP="LIGHT",
            EXPTIME=30.0,
            **{"DATE-OBS": f"2026-11-15T20:{i:02d}:00"},
        )
    scan = execute("calibration.scan", {"folder": str(folder)}, {}, Ctx())
    out = execute("calibration.run", {"frames": scan["frames"], "output_dir": str(folder / "cal")}, params, Ctx())
    return out


def _sky(n):
    rng = np.random.default_rng(2)
    e = rng.poisson(700.0 * GAIN, (n, 64, 64)) / GAIN
    return BIAS + e + rng.normal(0, RN / GAIN, e.shape)


def test_the_run_writes_planes_whose_variance_matches_the_scatter(tmp_path):
    lights = _sky(30)
    lights[0][5, 5] = 65000.0
    paths = _night(tmp_path, list(lights))
    with fits.open(paths[0]) as h:
        assert [x.name for x in h] == ["PRIMARY", "SCI", "VAR", "DQ"]
        assert h["SCI"].data.dtype.itemsize == 4 and h["DQ"].data.dtype.itemsize == 1
        assert h["SCI"].header["EXPTIME"] == 30.0  # the image's own header carries the keywords
    frames = [planes.read(p) for p in paths]
    assert frames[0].dq[5, 5] & planes.SATURATED and not frames[1].dq[5, 5]
    sci = np.stack([f.sci for f in frames])[:, 8:, 8:]
    var = np.mean([f.var for f in frames], axis=0)[8:, 8:]
    assert abs(np.mean(sci.var(axis=0, ddof=1)) / np.mean(var) - 1) < 0.1


def test_the_setting_off_writes_plain_fits(tmp_path):
    paths = _night(tmp_path, list(_sky(2)), write_planes=False)
    with fits.open(paths[0]) as h:
        assert len(h) == 1 and h[0].data.shape == (64, 64)
        assert "planes: not written (setting is off)" in [str(x) for x in h[0].header["HISTORY"]]
    assert planes_use.read(paths[0]) is None


def test_no_gain_writes_dq_only_and_says_so(tmp_path):
    paths = _night(tmp_path, list(_sky(2)), gain=None)
    f = planes.read(paths[0])
    assert f.var is None and f.dq is not None
    assert any("no gain" in str(x) for x in f.header["HISTORY"])


def test_photometry_and_images_open_the_multi_extension_output(tmp_path):
    lights = [field(4.0, seed=100 + i) + BIAS for i in range(6)]
    lights[3][int(STARS[0][1]), int(STARS[0][0])] = 65000.0  # the target's centre saturates in frame 3
    paths = _night(tmp_path, lights)
    data, header, index = fitsio.read_image(paths[0])
    assert index == 1 and data.shape == (200, 200) and header["EXPTIME"] == 30.0 and data.dtype == np.float32
    xy = [s[:2] for s in STARS]
    lc = light_curve(paths, xy[0], xy[1:3], 6, 15, 20, gain=GAIN)
    assert ["S" in row[0] for row in lc["flags"]] == [i == 3 for i in range(6)]  # (the spike may also read as "C")


def test_an_old_plain_calibrated_file_still_reads(tmp_path):
    p = tmp_path / "old.fits"
    fits.PrimaryHDU(np.ones((20, 30), np.float32), fits.Header({"EXPTIME": 5.0})).writeto(p)
    data, header, index = fitsio.read_image(p)
    assert index == 0 and data.shape == (20, 30) and header["EXPTIME"] == 5.0
    assert planes.read(p).var is None and planes_use.read(p) is None


def _trail_lights():
    rng = np.random.default_rng(3)
    lights = [BIAS + 700.0 + rng.normal(0, 8, (256, 256)) for _ in range(2)]
    yy, xx = np.indices((256, 256))
    d = -(xx - 127.5) * np.sin(np.radians(30)) + (yy - 127.5) * np.cos(np.radians(30)) - 20.0
    lights[0] += 400.0 * np.exp(-(d**2) / 4.0)
    return lights, d


def test_trails_found_listed_and_flagged_in_dq(tmp_path):
    lights, d = _trail_lights()
    folder = tmp_path / "n"
    folder.mkdir()
    out = _run_night(folder, lights, find_trails=True)
    assert [t["file"] for t in out["trails"]] == ["l00.fits"] and abs(out["trails"][0]["angle"] - 30) < 1
    import json

    json.dumps(out["trails"])
    dq = planes.read(out["calibrated"][0]).dq
    hit = (dq & planes.TRAIL) > 0
    assert hit[np.abs(d) < 1.5].all() and not hit[np.abs(d) > 15].any()
    assert not (planes.read(out["calibrated"][1]).dq & planes.TRAIL).any()


def test_option_off_never_searches(tmp_path, monkeypatch):
    from astrowb.calibration import trails

    monkeypatch.setattr(trails, "find", lambda *a, **k: 1 / 0)
    folder = tmp_path / "n"
    folder.mkdir()
    out = _run_night(folder, _trail_lights()[0])
    assert out["trails"] == []

"""CAL-5 item 2: the rejection each master kind gets without thought, and "as before" kept exactly."""

import numpy as np
import pytest
from astropy.io import fits

from astrowb.calibration import master_method, masters
from astrowb.compute.combine import clipped_mean


def _write(path, data, **hdr):
    fits.PrimaryHDU(np.asarray(data, np.float32), fits.Header(hdr)).writeto(path)
    return str(path)


def test_the_chooser_follows_the_rule():
    pick = master_method.choose
    assert pick("bias", 5)[0] == "avsigclip" and pick("bias", 10)[0] == "sigclip"
    assert pick("dark", 8)[:2] == ("sigclip", {"lsigma": np.inf, "hsigma": 3.0})
    method, params, text = pick("dark", 8, gain=1.5, read_noise=6.0)
    assert method == "ccdclip" and params["lsigma"] == np.inf and params["gain"] == 1.5 and "high side" in text
    assert pick("dark", 8, gain=1.5)[0] == "sigclip"  # read noise unknown
    assert pick("flat", 4)[0] == "minmax" and pick("flat", 5)[:2] == ("sigclip", {"lsigma": 3.0, "hsigma": 3.0})
    assert pick("flat", 2)[0] == "none"
    assert pick("bias", 20, "as before") is None and pick("flat", 20, "pclip")[0] == "pclip"


def test_a_cosmic_ray_in_a_dark_stack_is_removed_on_the_high_side_only(tmp_path):
    rng = np.random.default_rng(1)
    frames = []
    for i in range(6):
        d = 100 + rng.normal(0, 2, (20, 24))
        d[5, 5] += 800 if i == 2 else 0  # a hit in one frame
        frames.append(_write(tmp_path / f"d{i}.fits", d, EXPTIME=30.0, IMAGETYP="Dark Frame"))
    how = master_method.choose("dark", 6)
    img, h = masters.master_dark(frames, how=how)
    assert abs(img[5, 5] - 100) < 5 and "high side only" in h["COMBINE"]
    assert abs(float(np.median(img)) - 100) < 1


def test_flats_of_different_levels_are_scaled_and_a_star_is_rejected(tmp_path):
    rng = np.random.default_rng(2)
    frames = []
    for i, level in enumerate((1000, 3000, 2000, 5000, 4000, 1500)):
        f = level * (1 + 0.1 * np.linspace(0, 1, 30))[None, :] * np.ones((20, 30)) + rng.normal(
            0, level * 0.002, (20, 30)
        )
        f[8, 8] += 2 * level if i == 3 else 0  # a star in twilight
        frames.append(_write(tmp_path / f"f{i}.fits", f, EXPTIME=2.0, IMAGETYP="Flat Field"))
    img, h = masters.master_flat(frames, how=master_method.choose("flat", 6))
    assert np.median(img) == pytest.approx(1.0) and abs(img[8, 8] - img[8, 7]) < 0.02
    assert h["COMBINE"].startswith("sigclip")


def test_as_before_equals_the_old_clipped_mean_and_the_header_says_so(tmp_path):
    rng = np.random.default_rng(3)
    frames = [
        _write(tmp_path / f"b{i}.fits", 300 + rng.normal(0, 3, (16, 16)), IMAGETYP="Bias Frame") for i in range(7)
    ]
    img, h = masters.master_bias(frames, how=master_method.choose("bias", 7, "as before"))
    stack = np.stack([fits.getdata(p).astype(np.float32) for p in frames])
    assert np.array_equal(img, clipped_mean(stack, 3.0, 5)[0])
    assert h["COMBINE"] == "sigma-clipped mean"
    _, auto = masters.master_bias(frames, how=master_method.choose("bias", 7))
    assert auto["COMBINE"] == "avsigclip 3 sigma, mean"


def test_the_run_records_the_method_of_each_master(tmp_path):
    from astrowb.engine.steps import execute

    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    night = tmp_path / "n"
    night.mkdir()
    rng = np.random.default_rng(4)
    for i in range(5):
        _write(night / f"bias{i}.fits", 300 + rng.normal(0, 3, (16, 16)), IMAGETYP="Bias Frame", EXPTIME=0.0)
    _write(night / "light.fits", 400 + rng.normal(0, 3, (16, 16)), IMAGETYP="Light Frame", EXPTIME=10.0)
    frames = execute("calibration.scan", {"folder": str(night)}, {}, Ctx())["frames"]
    run = {"frames": frames, "output_dir": str(tmp_path / "cal")}
    out = execute("calibration.run", run, {"master_combine": "auto"}, Ctx())
    assert list(out["master_methods"].values()) == ["avsigclip 3 sigma, mean"]
    assert fits.getheader(out["masters"][0])["COMBINE"] == "avsigclip 3 sigma, mean"


def test_pick_uses_only_a_gain_in_electrons_per_adu(tmp_path):
    frames = [_write(tmp_path / f"d{i}.fits", np.full((8, 8), 5.0), GAIN=100, RDNOISE=6.0) for i in range(5)]
    assert master_method.pick("dark", frames, {"master_combine": "auto"})[0] == "sigclip"  # GAIN is a camera setting
    assert master_method.pick("dark", frames, {"master_combine": "auto", "gain": 1.2})[0] == "ccdclip"
    assert master_method.pick("dark", frames, {"master_combine": "as before"}) is None

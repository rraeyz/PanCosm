"""CAL-6: synthetic masters with one known defect each, reported with the right number within 10 %."""

import numpy as np
import pytest

from astrowb.calibration import quality

SHAPE = (400, 500)


def test_banding_of_2_adu():
    rng = np.random.default_rng(1)
    bias = 300 + rng.normal(0, 3, SHAPE) + rng.normal(0, 2.0, SHAPE[0])[:, None]  # rows offset by 2 ADU (σ)
    assert quality.banding(bias)["rows"] == pytest.approx(2.0, rel=0.1)
    assert quality.banding(bias)["columns"] < 0.3
    r = quality.report("bias", bias, n_inputs=20, single_noise=3 * np.sqrt(20))
    assert not r["banding"]["ok"]


def test_500_hot_pixels_and_the_dark_current():
    rng = np.random.default_rng(2)
    bias = 300 + rng.normal(0, 2, SHAPE)
    dark = bias + 0.1 * 300 / 1.5 + rng.normal(0, 2, SHAPE)  # 0.1 e⁻/s over 300 s, gain 1.5 e⁻/ADU
    ys, xs = rng.integers(0, SHAPE[0], 500), rng.integers(0, SHAPE[1], 500)
    flat_idx = np.unique(ys * SHAPE[1] + xs)
    dark.ravel()[flat_idx] += rng.uniform(200, 2000, len(flat_idx))
    assert quality.hot_pixels(dark)["count"] == pytest.approx(len(flat_idx), rel=0.1)
    assert quality.dark_current(dark, bias, 300, gain=1.5) == pytest.approx(0.1, rel=0.1)
    r = quality.report("dark", dark, bias=bias, exptime=300, gain=1.5)
    assert r["hot_pixels"]["value"] == pytest.approx(len(flat_idx), rel=0.1) and r["dark_current"]["value"] > 0.09


def test_a_flat_at_95_percent_and_a_dust_mote_of_3_percent():
    rng = np.random.default_rng(3)
    yy, xx = np.indices(SHAPE)
    vignetting = 1 - 0.15 * (np.hypot(xx - 250, yy - 200) / 320) ** 2
    mote = 1 - 0.03 * np.exp(-((xx - 120) ** 2 + (yy - 300) ** 2) / (2 * 6.0**2))
    flat = 30000 * vignetting * mote + rng.normal(0, 30, SHAPE)
    motes = quality.dust(flat)
    assert motes and motes[0]["depth"] == pytest.approx(0.03, rel=0.15)
    assert abs(motes[0]["x"] - 120) < 2 and abs(motes[0]["y"] - 300) < 2
    levels = quality.flat_levels([30000, 62000], full_well=65000)
    assert levels[0]["ok"] and not levels[1]["ok"] and levels[1]["share"] == pytest.approx(0.954, abs=0.001)
    r = quality.report("flat", flat, input_medians=[30000, 62000], full_well=65000)
    assert not r["flat_levels"]["ok"] and r["dust"]["value"] == pytest.approx(0.03, rel=0.15)
    noise = quality.flat_noise(flat, n_inputs=10, level_adu=30000, gain=1.5)
    assert noise["per_pixel"] == pytest.approx(1 / np.sqrt(10 * 30000 * 1.5)) and noise["aperture"] < noise["per_pixel"]


def test_a_clean_bias_has_no_amber():
    rng = np.random.default_rng(4)
    bias = 300 + rng.normal(0, 3 / np.sqrt(20), SHAPE)
    r = quality.report("bias", bias, n_inputs=20, single_noise=3.0)
    assert all(v["ok"] for v in r.values()), r


def test_the_run_reports_each_master_and_the_window_says_the_ambers(tmp_path, qapp):
    from astropy.io import fits

    from astrowb.engine.steps import execute
    from astrowb.ui.calibrate_page import CalibratePage

    rng = np.random.default_rng(6)
    for i in range(6):
        fits.PrimaryHDU((300 + rng.normal(0, 3, (120, 160))).astype(np.float32),
                        fits.Header({"IMAGETYP": "BIAS"})).writeto(tmp_path / f"b{i}.fits")  # fmt: skip
        yy, xx = np.indices((120, 160))
        flat = (
            300 + 30000 * (1 - 0.06 * np.exp(-((xx - 80) ** 2 + (yy - 60) ** 2) / 50)) + rng.normal(0, 60, (120, 160))
        )
        fits.PrimaryHDU(flat.astype(np.float32), fits.Header({"IMAGETYP": "FLAT", "EXPTIME": 1.0})).writeto(
            tmp_path / f"f{i}.fits"
        )
    fits.PrimaryHDU((800 + rng.normal(0, 10, (120, 160))).astype(np.float32),
                    fits.Header({"IMAGETYP": "LIGHT", "EXPTIME": 5.0})).writeto(tmp_path / "l.fits")  # fmt: skip

    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    scan = execute("calibration.scan", {"folder": str(tmp_path)}, {}, Ctx())
    out = execute("calibration.run", {"frames": scan["frames"], "output_dir": str(tmp_path / "cal")}, {}, Ctx())
    flat_qc = next(v for k, v in out["quality"].items() if "flat" in k)
    assert not flat_qc["dust"]["ok"] and flat_qc["dust"]["value"] > 0.04  # the 6 % mote
    page = CalibratePage()
    lines = page._quality_lines(out["quality"])
    assert lines and "dust shadow" in lines[0]

"""Frame quality on a simulated night: a blurred frame, a cloudy frame and a twilight frame are found."""

from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits

from astrowb.engine.steps import execute
from astrowb.photometry.quality import judge

RNG = np.random.default_rng(5)
STARS = [(RNG.uniform(20, 180), RNG.uniform(20, 140), RNG.uniform(3e3, 3e4)) for _ in range(40)]


def frame(path, sigma=1.5, transparency=1.0, sky=100.0, i=0):
    yy, xx = np.mgrid[:160, :200]
    img = np.full(xx.shape, sky)
    for x, y, f in STARS:
        img += transparency * f / (2 * np.pi * sigma**2) * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * sigma**2))
    img = RNG.poisson(np.clip(img, 0, None)).astype(np.float32)
    fits.PrimaryHDU(img, fits.Header({"DATE-OBS": f"2026-11-15T20:{i:02d}:00", "EXPTIME": 30.0})).writeto(path)
    return str(path)


class Ctx:
    def progress(self, *a):
        pass

    def check(self):
        pass


def test_bad_frames_are_found(tmp_path):
    paths = [frame(tmp_path / f"f{i}.fits", i=i) for i in range(6)]
    paths.append(frame(tmp_path / "blur.fits", sigma=3.5, i=6))
    paths.append(frame(tmp_path / "cloud.fits", transparency=0.03, i=7))
    paths.append(frame(tmp_path / "twilight.fits", sky=2000.0, i=8))
    out = execute("photometry.quality", {"images": paths}, {}, Ctx())
    rows = {Path(r["file"]).name: r for r in out["quality"]}
    assert rows["f0.fits"]["fwhm"] == pytest.approx(2.355 * 1.5, rel=0.15)  # FWHM of the simulated stars
    assert rows["blur.fits"]["why"] == ["stars blurred"]
    assert rows["cloud.fits"]["why"] in (["no stars"], ["few stars (clouds?)"])  # thick clouds: nothing left
    assert "bright sky" in rows["twilight.fits"]["why"]
    assert sorted(Path(p).name for p in out["good"]) == [f"f{i}.fits" for i in range(6)]


def test_judge_handles_empty_frames():
    rows = judge([{"fwhm": None, "stars": 0, "background": 10.0}, {"fwhm": 3.0, "stars": 20, "background": 10.0}])
    assert rows[0]["why"] == ["no stars"] and rows[1]["good"]


def test_photometry_page_leaves_out_bad_frames(qtbot, tmp_path):
    from astrowb.ui.photometry_page import PhotometryPage

    page = PhotometryPage()
    qtbot.addWidget(page)
    paths = [frame(tmp_path / f"g{i}.fits", i=i) for i in range(3)] + [frame(tmp_path / "b.fits", sigma=3.5, i=3)]
    page.set_images(paths)
    rows = execute("photometry.quality", {"images": paths}, {}, Ctx())["quality"]
    page.show_quality(rows)
    assert page.result.text().startswith("3 of 4 frames are good.") and "stars blurred" in page.result.text()
    page._drop_bad()  # unticked in the frame list, not deleted: the frame numbers of marked stars stay valid
    assert len(page.images) == 4 and all("b.fits" not in p for p in page._series())
    assert "3 of them used" in page.images_label.text()


def test_night_flags():
    from astrowb.photometry.quality import night_flags

    n = 120
    rng = np.random.default_rng(3)
    ensemble = 1e6 * (1 + 0.01 * rng.normal(size=n))
    ensemble[40:46] *= 0.6  # a cloud: −40 % for six frames
    fwhm = 3.0 + 0.05 * rng.normal(size=n)
    fwhm[90:] += np.linspace(0, 3, 30)  # the focus drifts at the end
    x = 100 + 0.1 * rng.normal(size=n)
    y = 100 + 0.1 * rng.normal(size=n)
    x[70:] += 25  # a meridian flip moves the field
    flags, verdict = night_flags(ensemble, fwhm, x, y, peak=np.full(n, 30000.0), linearity=50000)
    assert flags["cloud"] == list(range(40, 46)) and flags["jump"] == [70] and flags["near_saturation"] == []
    assert flags["seeing"] and min(flags["seeing"]) >= 100
    assert verdict.startswith("6 frames behind cloud")
    quiet, line = night_flags(1e6 * (1 + 0.01 * rng.normal(size=n)))
    assert quiet["cloud"] == [] and line == "no frame flagged"


def test_checks_from_a_light_curve():
    from astrowb.photometry.quality import lc_checks

    n = 60
    comp = np.full((n, 3), 1e5)
    comp[20:25] *= 0.5
    lc = {"comp_flux": comp.tolist(), "fwhm": [3.0] * n, "xy": [[[100.0, 100.0], [50.0, 50.0]]] * n,
          "peak": [[20000.0, 1.0]] * n, "saturation": 60000.0}  # fmt: skip
    flags, verdict = lc_checks(lc)
    assert flags["cloud"] == list(range(20, 25)) and not flags["jump"] and not flags["near_saturation"]

"""Flat-darks (as in AstroImageJ / Siril): with no bias frames, darks taken at the flats' exposure are matched to the
flats and darks at the lights' exposure to the lights, so both lose their bias + dark current exactly."""

import time

import numpy as np
from astropy.io import fits


def _write(path, data, **hdr):
    fits.PrimaryHDU(np.asarray(data, np.float32), fits.Header(hdr)).writeto(path)


def test_flat_darks_without_bias(tmp_path):
    from astrowb.engine.core import Engine
    from astrowb.engine.project import Project
    from astrowb.engine.tasks import TaskQueue

    rng = np.random.default_rng(9)
    ny, nx = 60, 80
    yy, xx = np.mgrid[:ny, :nx]
    offset = 500 + 30 * np.sin(xx / 9)  # bias structure (no bias frames were taken)
    hot = np.zeros((ny, nx))
    hot[10, 20], hot[40, 60] = 4.0, 6.0  # dark current per second in two hot pixels
    flat = 0.8 + 0.4 * xx / nx  # vignetting
    d = tmp_path / "night"
    d.mkdir()
    for i in range(5):
        _write(
            d / f"flatdark_{i}.fits", offset + hot * 2 + rng.normal(0, 2, (ny, nx)), IMAGETYP="Dark Frame", EXPTIME=2.0
        )
        _write(
            d / f"dark_{i}.fits", offset + hot * 60 + rng.normal(0, 2, (ny, nx)), IMAGETYP="Dark Frame", EXPTIME=60.0
        )
        _write(
            d / f"flat_{i}.fits",
            offset + hot * 2 + 20000 * flat + rng.normal(0, 20, (ny, nx)),
            IMAGETYP="Flat Field",
            EXPTIME=2.0,
            FILTER="V",
        )
    _write(
        d / "light.fits",
        offset + hot * 60 + 1000 * flat + rng.normal(0, 2, (ny, nx)),
        IMAGETYP="Light Frame",
        EXPTIME=60.0,
        FILTER="V",
    )
    q = TaskQueue(max_workers=1)
    try:
        with Project(tmp_path / "p.astroproj") as project:
            out = Engine(project, q).run_chain(
                ["calibration.scan", "calibration.run"], {"folder": str(d), "output_dir": str(tmp_path / "cal")}, {}
            )
            time.sleep(0.2)
        cal = fits.getdata(tmp_path / "cal" / "light.fits")
        h = fits.getheader(tmp_path / "cal" / "light.fits")
        assert h["CALF"].startswith("master_flat") and h["CALD"].startswith("master_dark") and h["CALB"] == "none"
        assert np.std(cal / np.median(cal)) < 0.01  # flat field and offset gone: a flat sky remains
        assert abs(np.median(cal) - 1000 * np.median(flat)) < 15
        assert len(out["masters"]) == 3  # two darks (2 s for the flats, 60 s for the light) and the flat
    finally:
        q.shutdown()

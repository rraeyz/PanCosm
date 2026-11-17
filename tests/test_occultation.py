import numpy as np
import pytest
from astropy.io import fits

from astrowb.io.video import read_cube
from astrowb.photometry.occultation import fit_occultation


def test_square_well_25fps():
    dt, d0, r0 = 0.04, 3.013, 3.013 + 2.4
    t = np.arange(200) * dt
    f = np.clip(np.minimum(r0, t + dt / 2) - np.maximum(d0, t - dt / 2), 0, None) / dt
    y = 1 - 0.9 * f + np.random.default_rng(5).normal(0, 1 / 3, len(t))  # S/N 3 per frame
    res = fit_occultation(t, y, nboot=30, rng=1)
    assert abs(res["D"] - d0) < 0.05 and abs(res["R"] - r0) < 0.05
    assert abs(res["duration"] - 2.4) < 0.07
    assert res["D_err"] > 0 and res["R_err"] > 0 and res["mag_drop"] > 1.0


def test_fit_needs_points():
    with pytest.raises(ValueError):
        fit_occultation([0, 1], [1, 1])


def test_read_cube(tmp_path):
    p = tmp_path / "c.fits"
    h = fits.Header({"DATE-OBS": "2026-01-02T03:04:05"})
    fits.PrimaryHDU(np.arange(24, dtype=np.float32).reshape(3, 2, 4), h).writeto(p)
    frames, secs, start = read_cube(p, 0.04)
    assert frames.shape == (3, 2, 4) and np.allclose(secs, [0, 0.04, 0.08])
    assert start.startswith("2026-01-02T03:04:05")
    with pytest.raises(ValueError):
        read_cube(p, 0)


def test_occultation_step_through_the_engine():
    import json

    from astrowb.engine.steps import execute

    class Ctx:
        def progress(self, *a):
            pass

    dt, d0, r0 = 0.04, 1.5, 3.9
    t = np.arange(150) * dt
    f = np.clip(np.minimum(r0, t + dt / 2) - np.maximum(d0, t - dt / 2), 0, None) / dt
    y = 1 - 0.9 * f + np.random.default_rng(2).normal(0, 0.05, len(t))
    out = execute("timeseries.occultation", {"time": t.tolist(), "flux": y.tolist()}, {"nboot": 5}, Ctx())
    fit = out["occultation"]
    assert abs(fit["D"] - d0) < 0.02 and abs(fit["R"] - r0) < 0.02
    json.dumps(out)  # the project log stores step outputs as JSON

"""PHO-42: a faint target measured on running stacks of N frames: the scatter falls as √N, the times are the
groups' mean mid-times."""

import numpy as np
from astropy.io import fits

from astrowb.engine.steps import execute


class Ctx:
    def progress(self, *a):
        pass

    def check(self):
        pass


def test_running_stacks_beat_the_noise_by_root_n(tmp_path):
    rng = np.random.default_rng(5)
    yy, xx = np.mgrid[:90, :120]

    def star(x, y, f):
        return f * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 1.6**2)) / (2 * np.pi * 1.6**2)

    paths = []
    for i in range(96):
        dx = 0.05 * i  # a slow drift the alignment takes out
        img = 400 + star(40 + dx, 45, 1500) + star(85 + dx, 40, 4e5) + star(70 + dx, 70, 4e5)
        h = fits.Header({"DATE-OBS": f"2026-01-01T{1 + i // 60:02d}:{i % 60:02d}:00", "EXPTIME": 60.0})
        fits.PrimaryHDU(rng.poisson(img).astype(np.float32), h).writeto(tmp_path / f"f{i:03d}.fits")
        paths.append(str(tmp_path / f"f{i:03d}.fits"))
    inputs = {"images": paths, "target_xy": [40, 45], "comps_xy": [[85, 40], [70, 70]]}
    params = {"r_ap": 3.0, "r_in": 7.0, "r_out": 11.0, "gain": 1.0}
    one = execute("photometry.light_curve", inputs, params, Ctx())["light_curve"]
    four = execute("photometry.light_curve", inputs, params | {"combine": 4}, Ctx())["light_curve"]
    s1, s4 = np.std(one["rel_flux"]) / np.mean(one["rel_flux"]), np.std(four["rel_flux"]) / np.mean(four["rel_flux"])
    assert len(four["time"]) == 24 and 0.4 < s4 / s1 < 0.7  # √4 = 2 (24 points: ± 15 %)
    mid_first_group = np.mean(one["time"][:4])
    assert abs(four["time"][0] - mid_first_group) * 86400 < 1.0
    err1, err4 = np.median(one["rel_flux_err"]), np.median(four["rel_flux_err"])
    assert 0.4 < err4 / err1 < 0.6  # the summed counts keep the gain: the predicted errors follow


def test_a_centroid_that_jumps_away_from_the_field_follows_it():
    from astrowb.photometry.lightcurve import _off_the_field

    pred = np.array([[40.0, 45.0], [85.0, 40.0], [70.0, 70.0], [20.0, 20.0]])
    xy = pred + [[-2.3, -0.3], [0.7, 0.0], [0.6, 0.1], [0.65, 0.05]]  # the faint target pulled 3 px off
    out = _off_the_field(xy, pred, np.ones(4, bool))
    assert np.allclose(out[0], pred[0] + [0.65, 0.05], atol=0.05) and np.allclose(out[1:], xy[1:])  # the median move
    assert np.allclose(_off_the_field(xy[:2], pred[:2], np.ones(2, bool)), xy[:2])  # too few stars to judge

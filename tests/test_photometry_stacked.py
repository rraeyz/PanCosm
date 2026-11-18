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
    out, found = _off_the_field(xy, pred, np.ones(4, bool))
    assert np.allclose(out[0], pred[0] + [0.65, 0.05], atol=0.05) and np.allclose(out[1:], xy[1:])  # the median move
    assert list(found) == [False, True, True, True]
    assert np.allclose(_off_the_field(xy[:2], pred[:2], np.ones(2, bool))[0], xy[:2])  # too few stars to judge


def test_stacks_on_a_moving_track_gain_root_n_with_unbiased_times(tmp_path):
    from astrowb import timing
    from astrowb.photometry import moving_lc
    from astrowb.photometry.aperture import measure
    from astrowb.photometry.stacked import running_stacks

    rng = np.random.default_rng(3)
    yy, xx = np.mgrid[:80, :200]
    jd0, nf = 2461000.5, 48
    jds = jd0 + np.arange(nf) * 60 / 86400
    track = moving_lc.linear_track(jds, (jds[0], 30.0, 40.0), (jds[-1], 160.0, 44.0))  # 2.8 px per frame
    sky, f_obj = 100.0, 175.0  # S/N 3 in a 3-px aperture
    paths = []
    for i, (x, y) in enumerate(track):
        img = sky + f_obj * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 1.6**2)) / (2 * np.pi * 1.6**2)
        t = timing.Time(jds[i] - 30 / 86400, format="jd").isot
        h = fits.Header({"DATE-OBS": t, "EXPTIME": 60.0})
        fits.PrimaryHDU(rng.poisson(img).astype(np.float32), h).writeto(tmp_path / f"m{i:03d}.fits")
        paths.append(str(tmp_path / f"m{i:03d}.fits"))
    clicks = ((jds[0], 30.0, 40.0), (jds[-1], 160.0, 44.0))
    stacks = running_stacks(paths, 4, tmp_path / "s", Ctx(), track=clicks)
    assert len(stacks) == 12

    blank = [(x, y) for x in range(20, 181, 8) for y in (14, 66)]  # empty sky: the noise of an aperture sum

    def measured(file, xy):
        with fits.open(file) as h:
            f = measure(h[0].data.astype(float), [xy, *blank], 3.0, 7.0, 11.0, 1.0)[0]
            return f[0], f[1:], h[0].header

    one = [measured(p, track[i])[:2] for i, p in enumerate(paths)]
    f1, n1 = np.mean([f for f, _ in one]), np.std(np.concatenate([b for _, b in one]))
    got, mids = [], []
    for k, s_file in enumerate(stacks):
        mid = jds[4 * k : 4 * k + 4].mean()
        f, b, header = measured(s_file, moving_lc.linear_track([mid], *clicks)[0])
        got.append((f, b))
        mids.append(timing.mid_time(header).utc.jd - mid)
        assert header["EXPTIME"] == 240.0
    f4, n4 = np.mean([f for f, _ in got]), np.std(np.concatenate([b for _, b in got]))
    assert abs((f4 / n4) / (f1 / n1) / 2 - 1) < 0.10  # S/N 3 per frame -> 3 √4
    assert np.max(np.abs(mids)) * 86400 < 1.0

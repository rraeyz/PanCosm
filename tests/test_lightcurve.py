"""PER-1: the light-curve container, joining sets by fitted zero points, weights."""

import numpy as np
import pytest

from astrowb.timeseries import lightcurve as lcm


def two_sets(seed=1):
    rng = np.random.default_rng(seed)
    t1, t2 = np.sort(rng.uniform(0, 30, 800)), np.sort(rng.uniform(20, 60, 500))
    f = 2.37
    y1 = 12.0 + 0.2 * np.sin(2 * np.pi * f * t1) + rng.normal(0, 0.01, t1.size)
    y2 = 12.03 + 0.2 * np.sin(2 * np.pi * f * t2) + rng.normal(0, 0.03, t2.size)  # another camera: 0.03 mag off
    a = lcm.LightCurve(t1, y1, np.full(t1.size, 0.01), band=np.full(t1.size, "V"), magnitude=True)
    b = lcm.LightCurve(t2, y2, np.full(t2.size, 0.03), band=np.full(t2.size, "V"), magnitude=True)
    return a.append(b), f


def test_two_sets_join_with_the_offset_recovered():
    lc, f = two_sets()
    zp = lcm.zero_points(lc, [f])
    off, err = zp[1]
    assert zp[0] == (0.0, 0.0) and off == pytest.approx(0.03, abs=3 * err) and err < 0.003


def test_flags_units_tables_and_weights(tmp_path):
    lc, _f = two_sets()
    marked = lc.flagged(lc.time > 55, lcm.USER)
    assert marked.used.sum() < len(lc) and lc.used.all()  # the original is unchanged
    flux = lc.to_flux()
    back = flux.to_mag()
    assert np.allclose(back.value, lc.value) and np.allclose(back.error, lc.error)
    norm = lc.normalised()
    assert abs(np.median(norm.value[norm.set == 1])) < 1e-12
    t = marked.to_table()
    t.write(tmp_path / "lc.ecsv")
    from astropy.table import Table

    again = lcm.LightCurve.from_table(Table.read(tmp_path / "lc.ecsv"))
    assert again.magnitude and np.array_equal(again.flag, marked.flag) and again.band[0] == "V"
    assert np.allclose(lcm.weights(lc, "errors")[:2], 1e4)
    r = np.r_[np.zeros(len(lc) - 1), 1.0]
    w = lcm.weights(lc, "deviation", r)
    assert w[-1] < 1 and w[0] == 1
    assert np.all(np.isfinite(lcm.weights(lc, "set", np.random.default_rng(0).normal(size=len(lc)))))
    with pytest.raises(ValueError):
        lcm.weights(lc, "sigma")
    with pytest.raises(ValueError):
        lc.append(flux)
    assert np.all((lc.phase(0.4, 0.0) >= 0) & (lc.phase(0.4, 0.0) < 1))

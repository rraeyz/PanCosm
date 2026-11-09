import numpy as np
import pytest

from astrowb.photometry import multiplot as mp


def _lc(n=120, variable_comp=1):
    rng = np.random.default_rng(5)
    t = 2460000.3 + np.arange(n) / 1440.0
    trans = 1 - 0.01 * ((t - t.mean()) ** 2 < (15 / 1440) ** 2)
    comp = np.column_stack([1e5 * (1 + rng.normal(0, 1e-3, n)) for _ in range(3)])
    comp[:, variable_comp] *= 1 + 0.02 * np.sin(np.arange(n))  # a jittery comparison star
    tf = 5e4 * trans * (1 + rng.normal(0, 1e-3, n))
    rel = tf / comp.sum(axis=1)
    return {"time": t.tolist(), "target_flux": tf.tolist(), "target_flux_err": (0.001 * tf).tolist(),
            "comp_flux": comp.tolist(), "comp_flux_err": (0.001 * comp).tolist(), "rel_flux": rel.tolist(),
            "rel_flux_err": (0.0015 * rel).tolist(), "airmass": np.linspace(1.2, 1.6, n).tolist(),
            "extra": [{"name": "T5", "role": "check", "rel_flux": [1.0] * n, "rel_flux_err": [0.001] * n}]}  # fmt: skip


def test_series_named_as_aij():
    lc = _lc()
    keys = mp.available(lc)
    assert keys == ["rel_flux_T1", "rel_flux_T5", "Source-Sky_C2", "Source-Sky_C3", "Source-Sky_C4", "airmass"]
    y, e = mp.series(lc, "Source-Sky_C3")
    assert np.allclose(y, np.asarray(lc["comp_flux"])[:, 1]) and e is not None
    assert mp.series(lc, "rel_flux_T5")[0][0] == 1.0
    with pytest.raises(KeyError):
        mp.series(lc, "nothing")


def test_normalise_on_a_range_and_bin():
    t = np.arange(100) / 1440.0
    y = np.where(t < 50 / 1440, 2.0, 4.0)
    _, yn, _ = mp.prepare(t, y, norm=(0, 40 / 1440))
    assert yn[0] == 1.0 and yn[-1] == 2.0
    tb, yb, eb = mp.prepare(t, y, np.full(100, 0.1), norm=False, bin_n=10)
    assert len(tb) == 10 and yb[0] == 2.0 and np.isclose(eb[0], 0.1 / np.sqrt(10))
    tb, yb, _ = mp.prepare(t, y, norm=False, bin_minutes=5.0)
    assert len(tb) == 20 and np.isclose(tb[0], 2 / 1440)


def test_leaving_out_the_jittery_comparison_lowers_the_scatter():
    rows = mp.leave_each_out(_lc(variable_comp=1))
    assert rows[0][0] == 1  # the second comparison star
    full = dict(rows)[None]
    assert rows[0][1] < 0.5 * full


def test_template_round_trip(tmp_path):
    rows = [{"key": "rel_flux_T1", "colour": "#1f77b4", "normalise": True, "offset": 0.0}]
    p = mp.save_template(tmp_path / "a.plot.json", rows, bin_minutes=5, norm=(0.0, 1.5), spacing=0.02)
    doc = mp.load_template(p)
    assert doc["rows"] == rows and doc["norm_hours"] == [0.0, 1.5] and doc["bin_minutes"] == 5.0
    (tmp_path / "b.json").write_text("[1, 2]")
    with pytest.raises(ValueError):
        mp.load_template(tmp_path / "b.json")

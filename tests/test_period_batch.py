"""PER-17: many stars searched in one go."""

import numpy as np

from astrowb.timeseries import batch


def test_many_stars():
    rng = np.random.default_rng(0)
    curves, truth = [], []
    for i in range(20):
        t = np.sort(rng.uniform(0, 30, 300))
        p = rng.uniform(0.3, 5)
        y = 0.1 * np.sin(2 * np.pi * t / p) + rng.normal(0, 0.02, t.size)
        curves.append((f"star{i}", t, y, None))
        truth.append(p)
    curves.append(("flat", np.sort(rng.uniform(0, 30, 300)), rng.normal(0, 0.02, 300), None))
    rows = batch.search_all(curves, p_min=0.2, p_max=10)
    assert [r["name"] for r in rows][:2] == ["star0", "star1"]
    for r, p in zip(rows[:-1], truth, strict=True):
        assert abs(1 / r["period"] - 1 / p) < 1e-3 and r["fap"] < 1e-10  # 1e-3 c/d: about 3 σ_f here
    assert rows[-1]["fap"] > 1e-3

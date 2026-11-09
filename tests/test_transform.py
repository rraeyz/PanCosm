"""PHO-35: a B / V night with colour terms 0.05 and 0.10 — the transformed magnitudes within 0.005 mag of the truth,
the untransformed ones off by several hundredths."""

import numpy as np

from astrowb.photometry import transform
from astrowb.photometry.export import aavso_extended, ensemble_magnitudes

TB, TV = 0.05, 0.10  # (B − b) = TB (B − V) + Zb ; (V − v) = TV (B − V) + Zv


def night(seed=2):
    rng = np.random.default_rng(seed)
    n = 60
    t = np.linspace(2461000.30, 2461000.55, 2 * n)
    tb, tv = t[0::2], t[1::2]  # B and V frames in turn
    V_c = np.array([11.2, 11.8, 12.1, 12.5, 12.9])
    BV_c = np.array([0.30, 0.45, 0.60, 0.75, 0.90])
    B_c = V_c + BV_c
    bv_t = 1.20  # a red target
    v_true = 12.40 + 0.15 * np.sin(2 * np.pi * (tv - tv[0]) / 0.2)  # it varies
    b_true = 12.40 + bv_t + 0.15 * np.sin(2 * np.pi * (tb - tv[0]) / 0.2)

    def lc(times, true_t, cat, coeff):
        zp = 21.0 + 0.2 * (times - times[0]) + rng.normal(0, 0.003, len(times))  # extinction and thin cloud
        inst_c = cat[None] - coeff * BV_c[None] - zp[:, None]
        inst_t = true_t - coeff * bv_t - zp
        fc, ft = 10 ** (-0.4 * inst_c), 10 ** (-0.4 * inst_t)
        rel = ft / fc.sum(1)
        return {"jd_utc": times.tolist(), "rel_flux": rel.tolist(), "rel_flux_err": (rel * 0.002).tolist(),
                "comp_flux": fc.tolist()}  # fmt: skip

    return lc(tb, b_true, B_c, TB), lc(tv, v_true, V_c, TV), B_c, V_c, BV_c, b_true, v_true, bv_t


def test_a_b_v_night_transformed_on_every_frame():
    lc_b, lc_v, B_c, V_c, BV_c, b_true, v_true, bv_t = night()
    raw_v, _ = ensemble_magnitudes(lc_v, V_c)
    raw_b, _ = ensemble_magnitudes(lc_b, B_c)
    assert np.abs(raw_v - v_true).max() > 0.03 and np.abs(raw_b - b_true).max() > 0.015  # untransformed: off
    out = transform.transformed_pair(lc_b, lc_v, B_c, V_c, TB, TV, errors=(0.01, 0.01))
    (b, _), (v, v_err) = out["a"], out["b"]
    assert np.abs(v - v_true).max() < 0.005 and np.abs(b - b_true).max() < 0.005
    assert np.abs(out["colour_b"] - bv_t).max() < 0.01
    assert np.all(v_err > 0.01 * abs(bv_t - BV_c.mean()) * 0.99)  # the coefficient's error is carried


def test_a_typed_colour_and_the_aavso_report_says_transformed():
    lc_b, lc_v, B_c, V_c, BV_c, b_true, v_true, bv_t = night()
    v, _ = transform.transformed(lc_v, V_c, BV_c, bv_t, TV)
    assert np.abs(v - v_true).max() < 0.005
    terms = {"colour_c": BV_c, "colour_t": bv_t, "coefficient": TV, "name": "Tv_bv"}
    text = aavso_extended(lc_v, "NY Vir", "XYZ", "V", V_c, transform=terms)
    row = text.splitlines()[-1].split(",")
    assert row[5] == "YES" and abs(float(row[2]) - v_true[-1]) < 0.005 and "Tv_bv=0.100" in row[-1]

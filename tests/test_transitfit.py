"""PHO-26: the exact transit fitted with detrending, its derived values, BIC choosing the detrending."""

import numpy as np
import pytest

from astrowb.occult.model import transit
from astrowb.photometry import transitfit as tf

P, TC, K, A, B = 1.42, 2459500.6123, 0.145, 6.3, 0.5


def night(seed):
    rng = np.random.default_rng(seed)
    t = np.linspace(TC - 0.12, TC + 0.12, 265)
    airmass = 1.1 + 2.0 * ((t - TC + 0.1) ** 2)
    inc = np.degrees(np.arccos(B / A))
    f = (
        1.003
        * transit(t - TC, P, 0.0, K, A, inc, "quadratic", (0.45, 0.2))
        * np.exp(-0.012 * (airmass - airmass.mean()) / airmass.std())
    )
    return t, f + rng.normal(0, 0.0015, t.size), np.full(t.size, 0.0015), airmass


def test_parameters_within_their_errors_and_bic_picks_the_airmass_term():
    inside = 0
    for seed in range(40):
        t, f, e, am = night(seed)
        start = {"tc": TC + 0.004, "k": 0.13, "a_rs": 6.0, "b": 0.4, "u1": 0.45, "u2": 0.2}
        got = tf.fit(t, f, e, P, start, detrend={"airmass": am})
        v, s = got["values"], got["errors"]
        inside += all(abs(v[n] - truth) < 2.5 * s[n] for n, truth in (("tc", TC), ("k", K), ("a_rs", A), ("b", B)))
    assert inside >= 36  # 2.5 σ in every one of four parameters
    t, f, e, am = night(1)
    bics = tf.compare_detrending(t, f, e, P, start, {"none": None, "airmass": {"airmass": am}})
    assert bics["airmass"] < bics["none"] - 10
    d = got["derived"]
    assert d["depth_ppt"] == pytest.approx(K**2 * 1000, rel=0.1) and d["t14_h"] > d["t23_h"] > 0
    assert 0.5 < got["beta"] < 1.5 and got["chi2r"] == pytest.approx(1.0, abs=0.2)
    rj, re = tf.planet_radius(0.1, 1.0)
    assert rj == pytest.approx(0.973, abs=0.01) and re == pytest.approx(10.9, abs=0.1)


def test_a_prior_pulls_the_parameter():
    t, f, e, am = night(3)
    start = {"tc": TC, "k": 0.14, "a_rs": 6.3, "b": 0.5}
    free = tf.fit(t, f, e, P, start, detrend={"airmass": am})
    held = tf.fit(t, f, e, P, start, detrend={"airmass": am}, priors={"a_rs": (6.3, 0.05)})
    assert held["errors"]["a_rs"] < free["errors"]["a_rs"] and abs(held["values"]["a_rs"] - 6.3) < 0.15


def test_the_step_on_a_light_curve():
    from astrowb.engine import builtin  # noqa: F401
    from astrowb.engine.steps import execute

    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    t, f, e, am = night(5)
    lc = {"time": t.tolist(), "rel_flux": f.tolist(), "rel_flux_err": e.tolist(), "airmass": am.tolist()}
    out = execute("photometry.transit_fit", {"light_curve": lc}, {"period": P, "k": 0.13, "a_rs": 6.0, "b": 0.4},
                  Ctx())["transit"]  # fmt: skip
    assert out["values"]["tc"] == pytest.approx(TC, abs=4 * out["errors"]["tc"])
    with pytest.raises(ValueError, match="unknown detrending"):
        execute("photometry.transit_fit", {"light_curve": lc}, {"period": P, "detrend": "humidity"}, Ctx())


def test_exoclock_file_is_detrended_and_valid(tmp_path):
    """PHO-27: the ExoClock upload divides by the fitted baseline and airmass trend; its validator finds broken
    files."""
    from astrowb.photometry.reports import exoclock

    t, f, e, am = night(2)
    fit = tf.fit(t, f, e, P, {"tc": TC, "k": 0.14, "a_rs": 6.3, "b": 0.5}, detrend={"airmass": am})
    lc = {"time": t.tolist(), "time_scale": "BJD_TDB", "rel_flux": f.tolist(), "rel_flux_err": e.tolist()}
    path = exoclock.write(lc, tmp_path / "ExoClock.txt", fit)
    assert exoclock.validate(path) == []
    data = np.loadtxt(path)
    out = np.abs(t - TC) > 0.08  # out of transit: flat at 1 within the noise once the airmass trend is gone
    assert np.mean(data[out, 1]) == pytest.approx(1.0, abs=5e-4) and np.std(data[out, 1]) < 0.0018
    assert "Mid-transit time (BJD_TDB)" in exoclock.form(lc, fit, 60, "R")
    (tmp_path / "bad.txt").write_text("# x\n2459500.1 1.0 0.001\n2459500.0 1.0\n2459500.2 3.0 0.001\n")
    assert exoclock.validate(tmp_path / "bad.txt") == ["row 2: 2 columns, 3 expected",
                                                       "row 3: flux 3.0 or error 0.001 out of range"]  # fmt: skip
    with pytest.raises(ValueError, match="BJD_TDB"):
        exoclock.write(lc | {"time_scale": "JD_UTC"}, tmp_path / "x.txt")

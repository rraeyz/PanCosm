"""The eclipsing-binary light-curve model against exact geometry and brute-force integration."""

import numpy as np
import pytest

from astrowb.models import eb, fit


def overlap_area(d, ra, rb):
    """Exact area of two overlapping circles."""
    if d >= ra + rb:
        return 0.0
    if d <= abs(ra - rb):
        return np.pi * min(ra, rb) ** 2
    a1 = ra * ra * np.arccos((d * d + ra * ra - rb * rb) / (2 * d * ra))
    a2 = rb * rb * np.arccos((d * d + rb * rb - ra * ra) / (2 * d * rb))
    return a1 + a2 - 0.5 * np.sqrt((-d + ra + rb) * (d + ra - rb) * (d - ra + rb) * (d + ra + rb))


@pytest.mark.parametrize("ra, rb", [(0.1, 0.1), (0.05, 0.12), (0.2, 0.08)])
def test_uniform_disc_matches_exact_overlap(ra, rb):
    for d in np.linspace(0, ra + rb + 0.01, 57):
        got = eb.eclipsed_fraction(d, ra, rb)[0]
        assert got == pytest.approx(overlap_area(d, ra, rb) / (np.pi * rb * rb), abs=1e-7)


def test_limb_darkened_matches_brute_force():
    rb, ra, u1, u2 = 0.1, 0.06, 0.45, 0.2
    n = 1601
    x = np.linspace(-rb, rb, n)
    xx, yy = np.meshgrid(x, x)
    r = np.hypot(xx, yy)
    mu = np.sqrt(np.clip(1 - (r / rb) ** 2, 0, 1))
    img = np.where(r <= rb, 1 - u1 * (1 - mu) - u2 * (1 - mu) ** 2, 0.0)
    for d in (0.0, 0.03, 0.07, 0.12, 0.155):
        covered = np.hypot(xx - d, yy) <= ra
        brute = img[covered].sum() / img.sum()
        assert eb.eclipsed_fraction(d, ra, rb, u1, u2)[0] == pytest.approx(brute, abs=3e-4)


def test_light_curve_geometry():
    p, t0 = 2.5, 100.0
    t = t0 + np.linspace(-0.6, 1.9, 4001)
    f = eb.light_curve(t, p, t0, 0.12, 0.09, 89.5, j=0.6, ld1=(0.4, 0.2), ld2=(0.5, 0.2))
    assert f.max() == pytest.approx(1.0, abs=1e-12)
    i_min = np.argmin(f)
    assert abs(t[i_min] - t0) < 1e-3  # primary minimum at t0
    sec = np.abs(t - (t0 + p / 2)) < 0.2
    bottom = t[sec][f[sec] < f[sec].min() + 1e-9]  # the secondary is total here: flat bottom
    assert abs(bottom.mean() - (t0 + p / 2)) < 1e-3  # circular: secondary at phase 0.5
    assert f[i_min] < f[sec].min()  # the hotter primary eclipse is deeper
    # eccentric: secondary displaced by ~ (2P/pi) e cos(omega)
    ecc, om = 0.1, 30.0
    f2 = eb.light_curve(t, p, t0, 0.12, 0.09, 89.5, j=0.6, e=ecc, omega_deg=om)
    near = np.abs(t - (t0 + p / 2)) < 0.4
    t_sec = t[near][f2[near] < f2[near].min() + 1e-9].mean()
    assert t_sec - (t0 + p / 2) == pytest.approx(2 * p / np.pi * ecc * np.cos(np.radians(om)), abs=0.01)
    # total light conserved with third light
    f3 = eb.light_curve(t, p, t0, 0.12, 0.09, 89.5, j=0.6, l3=0.3)
    f0 = eb.light_curve(t, p, t0, 0.12, 0.09, 89.5, j=0.6)
    assert np.allclose(f3, 0.7 * f0 + 0.3)


def test_transit_depth_small_planet():
    k, u1, u2 = 0.1, 0.4, 0.25
    f = eb.light_curve([0.0], 3.0, 0.0, 0.1, 0.1 * k, 90.0, j=0.0, ld1=(u1, u2))[0]
    depth = 1 - f
    # small-planet limit at disc centre: k^2 I(1) / <I>
    assert depth == pytest.approx(k * k / (1 - u1 / 3 - u2 / 6), rel=0.01)


def test_fit_recovers_a_detached_binary():
    from astrowb.models import fit

    rng = np.random.default_rng(12)
    truth = {
        "period": 3.1,
        "t0": 2459000.4,
        "r_sum": 0.25,
        "k": 0.75,
        "incl": 87.2,
        "j": 0.7,
        "ecosw": 0.01,
        "esinw": -0.02,
        "l3": 0.0,
    }
    t = np.sort(rng.uniform(2459000, 2459060, 3000))
    clean = fit.model(t, truth, (0.45, 0.2), (0.5, 0.2))
    flux = 1.3 * clean + rng.normal(0, 0.002, len(t))
    start = truth | {
        "r_sum": 0.22,
        "k": 0.9,
        "incl": 85.0,
        "j": 0.5,
        "t0": truth["t0"] + 0.003,
        "ecosw": 0.0,
        "esinw": 0.0,
    }
    r = fit.fit_light_curve(
        t,
        flux,
        np.full(len(t), 0.002),
        start,
        {"t0", "r_sum", "k", "incl", "j", "ecosw", "esinw"},
        (0.45, 0.2),
        (0.5, 0.2),
    )
    for n in ("t0", "r_sum", "k", "incl", "j", "ecosw", "esinw"):
        assert abs(r["params"][n] - truth[n]) < 4 * r["errors"][n] + 1e-9, n
    assert r["scale"] == pytest.approx(1.3, rel=1e-3) and 0.8 < r["chi2r"] < 1.2


def test_fit_transit():
    from astrowb.models import fit

    rng = np.random.default_rng(13)
    truth = {
        "period": 2.15,
        "t0": 2459100.2,
        "r_sum": 0.165,
        "k": 0.1,
        "incl": 88.9,
        "j": 0.0,
        "ecosw": 0.0,
        "esinw": 0.0,
        "l3": 0.0,
    }
    t = truth["t0"] + np.linspace(-0.12, 0.12, 600)
    flux = fit.model(t, truth, (0.4, 0.25)) + rng.normal(0, 0.001, len(t))
    r = fit.fit_light_curve(
        t, flux, None, truth | {"r_sum": 0.15, "k": 0.12, "incl": 87.0}, {"t0", "r_sum", "k", "incl"}, (0.4, 0.25)
    )
    assert r["params"]["k"] == pytest.approx(0.1, abs=4 * r["errors"]["k"])
    assert abs(r["params"]["t0"] - truth["t0"]) * 86400 < 4 * r["errors"]["t0"] * 86400 + 1


def test_absolute_dimensions():
    from astrowb.models import fit

    lc = {
        "params": {"incl": 90.0},
        "errors": {"incl": 0.0},
        "derived": {"r1": 0.1, "r2": 0.05},
        "derived_err": {"r1": 0.0, "r2": 0.0},
    }
    from astrowb.spectroscopy.orbit import sb2_dimensions

    # K2 for m1 sin^3 i = 1 with K1 = K2 / 2 (q = 0.5) and P = 10 d, e = 0
    k2 = (1.0 / sb2_dimensions(10.0, 0.0, 0.5, 1.0)[0]) ** (1 / 3)
    orb = {"period": 10.0, "e": 0.0, "k": 0.5 * k2, "k2": k2}
    a = sb2_dimensions(10.0, 0.0, 0.5 * k2, k2)[2]
    lc["derived"] = {"r1": 1 / a, "r2": 0.5 / a}
    d = fit.absolute_dimensions(lc, orb)
    assert d["m1"] == pytest.approx(1.0) and d["m2"] == pytest.approx(0.5) and d["r1"] == pytest.approx(1.0)
    assert d["logg1"] == pytest.approx(4.438, abs=0.002)  # the Sun (IAU 2015 nominal GM and R)


def test_light_curve_files_and_fit_step(tmp_path):
    import json

    from astrowb.engine.steps import execute
    from astrowb.models import data, fit

    truth = {
        "period": 1.7,
        "t0": 2459500.25,
        "r_sum": 0.3,
        "k": 0.6,
        "incl": 86.0,
        "j": 0.5,
        "ecosw": 0.0,
        "esinw": 0.0,
        "l3": 0.0,
    }
    rng = np.random.default_rng(3)
    t = np.sort(rng.uniform(2459500, 2459520, 1500))
    f = fit.model(t, truth) + rng.normal(0, 0.003, len(t))
    mag = 12.0 - 2.5 * np.log10(f)
    (tmp_path / "lc.txt").write_text("\n".join(f"{a:.6f} {b:.5f} 0.003" for a, b in zip(t, mag, strict=True)))
    tt, ff, ee, info = data.read_light_curve(tmp_path / "lc.txt")
    assert info["magnitudes"] and np.allclose(ff * np.median(f), f, rtol=1e-4) and ee is not None
    # our own CSV export has named columns
    (tmp_path / "lc.csv").write_text(
        "BJD_TDB,rel_flux,rel_flux_err\n" + "\n".join(f"{a:.6f},{2 * b:.6f},0.006" for a, b in zip(t, f, strict=True))
    )
    tt, ff, ee, info = data.read_light_curve(tmp_path / "lc.csv")
    assert not info["magnitudes"] and ee[0] == pytest.approx(0.006 / np.median(2 * f))

    class Ctx:
        def progress(self, *a):
            pass

    orb = {"period": 2.5, "period_err": 1e-5, "e": 0.0, "e_err": 0.0, "k": 95.0, "k_err": 0.5}
    orb |= {"k2": 140.0, "k2_err": 0.8}
    out = execute(
        "models.eb_fit",
        {
            "light_curve": str(tmp_path / "lc.csv"),
            "start": truth | {"incl": 84.0},
            "orbit": orb,
            "export_dir": str(tmp_path / "phoebe"),
        },
        {},
        Ctx(),
    )["model"]
    assert out["params"]["incl"] == pytest.approx(86, abs=4 * out["errors"]["incl"])
    assert out["absolute"]["m1"] > 1.2 and len(out["model_flux"]) == 1500
    start = json.loads((tmp_path / "phoebe" / "start.json").read_text())
    assert start["period@binary"] == 1.7 and "q@binary" in start
    mt, mf = data.read_model_curve(tmp_path / "phoebe" / "lc.txt")
    assert len(mt) == len(t)


@pytest.mark.slow
def test_mcmc_posterior_agrees_with_truth_and_least_squares():
    from astrowb.models import fit

    rng = np.random.default_rng(21)
    truth = {"period": 2.15, "t0": 2459100.2, "r_sum": 0.165, "k": 0.1, "incl": 88.9}
    truth |= {"j": 0.0, "ecosw": 0.0, "esinw": 0.0, "l3": 0.0}
    t = truth["t0"] + np.linspace(-0.12, 0.12, 200)
    err = np.full(len(t), 0.001)
    flux = fit.model(t, truth, (0.4, 0.25)) + rng.normal(0, 0.001, len(t))
    free = {"t0", "r_sum", "k"}
    r = fit.fit_light_curve(t, flux, err, truth | {"k": 0.12}, free, (0.4, 0.25))
    m = fit.mcmc(t, flux, err, r, free, (0.4, 0.25), steps=400, seed=3)
    assert 0.15 < m["acceptance"] < 0.8 and m["names"] == ["t0", "r_sum", "k"]
    for name in free:
        med, lo, hi = m["params"][name]
        assert abs(med - truth[name]) < 4 * max(lo, hi)  # the truth inside the posterior
        assert 0.4 < (lo + hi) / 2 / r["errors"][name] < 2.5  # the same size as the least-squares errors
    assert len(m["samples"]) > 100 and len(m["samples"][0]) == 3


def test_sb2_masses_follow_the_textbook_constants():
    """Hilditch (2001): m1 sin^3 i = 1.0361e-7 (1-e^2)^1.5 (K1+K2)^2 K2 P and a sin i = 1.9758e-2 (1-e^2)^0.5 (K1+K2) P
    (solar units, km/s, days; the constants change in the 4th digit with the adopted G M_sun and R_sun)."""
    from astrowb.spectroscopy.orbit import sb2_dimensions

    p, e, k1, k2 = 3.7, 0.3, 82.0, 117.0
    m1, m2, a = sb2_dimensions(p, e, k1, k2)
    assert m1 == pytest.approx(1.0361e-7 * (1 - e * e) ** 1.5 * (k1 + k2) ** 2 * k2 * p, rel=2e-4)
    assert m2 == pytest.approx(1.0361e-7 * (1 - e * e) ** 1.5 * (k1 + k2) ** 2 * k1 * p, rel=2e-4)
    assert a == pytest.approx(1.9758e-2 * (1 - e * e) ** 0.5 * (k1 + k2) * p, rel=1e-3)


def test_log_g_errors_follow_from_k2_p_r_and_i_only():
    """log g1 = log(G m1 / R1^2) is proportional to K2 / (P r1^2 sin i) (Southworth 2015): its error comes from those
    alone, (K1 + K2) cancels. The masses and the separation must therefore come from the same draws."""
    lc = {"params": {"incl": 86.0}, "errors": {"incl": 0.2}}
    lc |= {"derived": {"r1": 0.2, "r2": 0.15}, "derived_err": {"r1": 0.002, "r2": 0.002}}
    orb = {"period": 2.5, "period_err": 0.0, "e": 0.0, "e_err": 0.0, "k": 100.0, "k_err": 1.0, "k2": 130.0}
    orb["k2_err"] = 1.3
    d = fit.absolute_dimensions(lc, orb, n=40000)
    i = np.radians(86.0)
    analytic = np.hypot(np.hypot(0.01, 2 * 0.002 / 0.2), np.radians(0.2) / np.tan(i)) / np.log(10)
    assert d["logg1_err"] == pytest.approx(analytic, rel=0.1)


def test_small_planet_transit_depth_follows_mandel_agol():
    """Mandel & Agol (2002) small-planet limit: at the centre of the disc the depth is
    k^2 I(1) / <I> = k^2 / (1 - u1/3 - u2/6) for quadratic limb darkening."""
    from astrowb.models import eb

    k, u1, u2 = 0.02, 0.4, 0.25
    depth = eb.eclipsed_fraction(np.array([0.0]), k, 1.0, u1, u2)[0]
    assert depth == pytest.approx(k * k / (1 - u1 / 3 - u2 / 6), rel=1e-3)


def test_roche_check_flags_contact_and_distorted_binaries():
    assert fit.roche_check(0.15, 0.10)["level"] is None  # well detached (Algol-like radii)
    c = fit.roche_check(0.36, 0.36)  # W UMa radii, q = 1: lobe 0.379 (Eggleton 1983)
    assert c["level"] == "contact" and c["lobe1"] == pytest.approx(0.3789, abs=1e-4)
    assert fit.roche_check(0.27, 0.12)["level"] == "distorted"
    semi = fit.roche_check(0.22, 0.27, q=0.3)  # the light secondary fills its small lobe (0.281)
    assert semi["level"] == "contact" and semi["lobe2"] == pytest.approx(0.2810, abs=1e-3)


def test_long_exposures_are_modelled_by_averaging_over_each():
    """A transit recorded with 30-min exposures (TESS full frames): fitted without the exposure the inclination and
    the radii are biased (the smeared ingress looks grazing); with it they come back (Kipping 2010)."""
    from astrowb.models import fit
    from astrowb.models.orbit_terms import integrate_exposure

    truth = {"period": 2.15, "t0": 2459100.2, "r_sum": 0.165, "k": 0.1, "incl": 88.9, "j": 0.0, "ecosw": 0.0,
             "esinw": 0.0, "l3": 0.0}  # fmt: skip
    t = truth["t0"] + np.arange(-0.25, 0.25, 1800 / 86400) + 0.003
    t = np.concatenate([t + k * (truth["period"] + 0.0071) for k in range(12)])  # cadences fall on every phase
    smeared = integrate_exposure(lambda x: fit.model(x, truth, (0.4, 0.25)), t, 1800 / 86400, n=101)
    assert np.allclose(fit.model(t, truth | {"exposure": 1800}, (0.4, 0.25)), smeared, atol=2e-5)
    start = truth | {"r_sum": 0.15, "k": 0.11, "incl": 87.5}
    free = {"r_sum", "k", "incl"}
    plain = fit.fit_light_curve(t, smeared, None, start, free, (0.4, 0.25))
    long = fit.fit_light_curve(t, smeared, None, start | {"exposure": 1800}, free, (0.4, 0.25))
    assert abs(long["params"]["r_sum"] - 0.165) < 0.002 and abs(long["params"]["incl"] - 88.9) < 0.3
    assert abs(plain["params"]["r_sum"] - 0.165) > 5 * abs(long["params"]["r_sum"] - 0.165)

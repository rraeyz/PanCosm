"""Double-lined binaries: TODCOR velocities and the SB2 orbit, on simulations with known truth."""

import numpy as np
import pytest

from astrowb.spectroscopy import orbit, rv, sb2

C = 299792.458
WAVE = np.exp(np.arange(np.log(4800), np.log(5600), 1.5 / C))  # 1.5 km/s pixels (R ~ 100 000 / 2)
RNG = np.random.default_rng(3)
LINES1 = np.sort(RNG.uniform(4800, 5600, 250))  # a cool star: many lines
LINES2 = np.sort(RNG.uniform(4800, 5600, 60))  # a hotter companion: few, broader lines
DEPTH1 = RNG.uniform(0.1, 0.6, len(LINES1))
DEPTH2 = RNG.uniform(0.1, 0.4, len(LINES2))


def template(lines, depths, width, v=0.0, wave=WAVE):
    f = np.ones_like(wave)
    for lam, d in zip(lines, depths, strict=True):
        f -= d * np.exp(-0.5 * ((wave - lam * (1 + v / C)) / width) ** 2)
    return f


T1 = template(LINES1, DEPTH1, 0.08)
T2 = template(LINES2, DEPTH2, 0.20)


def composite(v1, v2, ratio=0.5, snr=100, rng=RNG):
    f = (template(LINES1, DEPTH1, 0.08, v1) + ratio * template(LINES2, DEPTH2, 0.20, v2)) / (1 + ratio)
    return f + rng.normal(0, 1 / snr, len(f))


@pytest.mark.parametrize("v1, v2", [(60.0, -90.0), (12.0, -20.0), (-45.0, 30.0)])
def test_todcor_recovers_both_velocities(v1, v2):
    r = sb2.todcor(WAVE, composite(v1, v2), WAVE, T1, WAVE, T2, -200, 200)
    assert r["rv1"] == pytest.approx(v1, abs=0.3) and r["rv2"] == pytest.approx(v2, abs=0.6)
    # the light ratio of the composite (secondary / primary) is 0.5 by construction
    assert r["flux_ratio"] == pytest.approx(0.5, rel=0.15)


def test_todcor_errors_describe_the_scatter():
    rng = np.random.default_rng(8)
    runs = [sb2.todcor(WAVE, composite(30.0, -50.0, rng=rng, snr=40), WAVE, T1, WAVE, T2, -100, 100) for _ in range(15)]
    v1, v2 = np.array([r["rv1"] for r in runs]), np.array([r["rv2"] for r in runs])
    e1, e2 = np.median([r["rv1_err"] for r in runs]), np.median([r["rv2_err"] for r in runs])
    assert 0.4 < np.std(v1) / e1 < 2.5 and 0.4 < np.std(v2) / e2 < 2.5
    assert (
        abs(v1.mean() - 30) < 3 * np.std(v1) / np.sqrt(15) + 0.1
        and abs(v2.mean() + 50) < 3 * np.std(v2) / np.sqrt(15) + 0.2
    )


def test_todcor_with_fixed_light_ratio():
    free = sb2.todcor(WAVE, composite(40.0, -60.0), WAVE, T1, WAVE, T2, -150, 150)
    fixed = sb2.todcor(WAVE, composite(40.0, -60.0), WAVE, T1, WAVE, T2, -150, 150, alpha=free["alpha"])
    assert fixed["rv1"] == pytest.approx(40, abs=0.3) and fixed["rv2"] == pytest.approx(-60, abs=0.6)


def test_plain_ccf_is_pulled_when_lines_blend_but_todcor_is_not():
    f = composite(12.0, -20.0, ratio=0.8)
    single = rv.ccf(WAVE, f, WAVE, T1, -200, 200)["rv"]
    both = sb2.todcor(WAVE, f, WAVE, T1, WAVE, T2, -200, 200)["rv1"]
    assert abs(both - 12) < abs(single - 12) or abs(both - 12) < 0.3


def test_sb2_orbit_recovers_truth():
    rng = np.random.default_rng(4)
    truth = {"period": 4.5, "t_peri": 2460100.3, "e": 0.2, "omega": 60.0, "k": 80.0, "k2": 120.0, "gamma": -15.0}
    t = np.sort(rng.uniform(2460100, 2460160, 24))
    v1 = orbit.rv_model(t, 4.5, truth["t_peri"], 0.2, 60.0, 80.0, -15.0) + rng.normal(0, 1.0, len(t))
    v2 = orbit.rv_model(t, 4.5, truth["t_peri"], 0.2, 240.0, 120.0, -15.0) + rng.normal(0, 2.0, len(t))
    fit = orbit.fit_sb2(t, v1, t, v2, np.full(len(t), 1.0), np.full(len(t), 2.0), period=4.49, e=0.1, omega_deg=90)
    for key in ("period", "e", "omega", "k", "k2", "gamma"):
        assert abs(fit[key] - truth[key]) < 4 * fit[key + "_err"] + 1e-9, key
    assert abs((fit["t_peri"] - truth["t_peri"] + 2.25) % 4.5 - 2.25) < 4 * fit["t_peri_err"]
    # masses from the true elements: m1 sin^3 i = P (K1+K2)^2 K2 (1-e^2)^1.5 / (2 pi G)
    p, kt = 4.5 * 86400, 200e3
    m1 = p * kt**2 * 120e3 * (1 - 0.04) ** 1.5 / (2 * np.pi * 6.67430e-11) / 1.98847e30
    assert abs(fit["m1_sin3i"] - m1) < 4 * fit["m1_sin3i_err"]
    assert fit["q"] == pytest.approx(80 / 120, abs=4 * fit["q_err"])
    assert 0.5 < fit["chi2r"] < 1.8


class _Ctx:
    def progress(self, *a):
        pass

    def check(self):
        pass


def test_rv_and_orbit_steps_in_sb2_mode(tmp_path):
    from astrowb.engine.steps import execute
    from astrowb.spectroscopy import spectrum_io

    spectrum_io.write(tmp_path / "t1.fits", WAVE, T1, np.full(len(WAVE), 0.01))
    spectrum_io.write(tmp_path / "t2.fits", WAVE, T2, np.full(len(WAVE), 0.01))
    paths = []
    for i, (v1, v2) in enumerate([(50.0, -70.0), (-30.0, 45.0)]):
        p = tmp_path / f"s{i}.fits"
        spectrum_io.write(p, WAVE, composite(v1, v2), np.full(len(WAVE), 0.01))
        paths.append(str(p))
    inputs = {"spectra": paths, "template": str(tmp_path / "t1.fits"), "template2": str(tmp_path / "t2.fits")}
    rows = execute("spectroscopy.rv", inputs, {"v_min": -120, "v_max": 120}, _Ctx())["rvs"]
    assert rows[0]["rv_obs"] == pytest.approx(50, abs=0.5) and rows[0]["rv2_obs"] == pytest.approx(-70, abs=1)
    assert rows[1]["rv_obs"] == pytest.approx(-30, abs=0.5) and rows[1]["rv2_obs"] == pytest.approx(45, abs=1)
    # templates that are real stars: their own velocities are put on the measured ones (TZ For with tau Ceti, -16.5)
    params = {"v_min": -120, "v_max": 120, "template_rv": -16.5, "template2_rv": 17.0}
    moved = execute("spectroscopy.rv", inputs, params, _Ctx())["rvs"]
    assert moved[0]["rv_obs"] == pytest.approx(rows[0]["rv_obs"] - 16.5, abs=1e-6)
    assert moved[0]["rv2_obs"] == pytest.approx(rows[0]["rv2_obs"] + 17.0, abs=1e-6)

    rng = np.random.default_rng(1)
    t = np.sort(rng.uniform(0, 30, 16))
    v1 = orbit.rv_model(t, 3.2, 0.7, 0.0, 90.0, 70.0, 5.0) + rng.normal(0, 0.5, len(t))
    v2 = orbit.rv_model(t, 3.2, 0.7, 0.0, 270.0, 95.0, 5.0) + rng.normal(0, 0.5, len(t))
    fit = execute(
        "spectroscopy.orbit", {"time": t.tolist(), "rv": v1.tolist(), "rv2": v2.tolist()}, {"period": 3.2}, _Ctx()
    )
    assert fit["orbit"]["k2"] == pytest.approx(95, abs=1.5) and fit["orbit"]["k"] == pytest.approx(70, abs=1.5)


def test_velocity_tab_shows_sb2(qtbot, tmp_path):
    from astrowb.ui.spectro_page import VelocityTab

    tab = VelocityTab()
    qtbot.addWidget(tab)
    rng = np.random.default_rng(2)
    t = np.sort(rng.uniform(2460000, 2460030, 10))
    rows = [
        {
            "file": f"s{i}.fits",
            "bjd": ti,
            "rv": None,
            "rv_obs": float(orbit.rv_model(ti, 3.0, 2460000.5, 0, 90, 60, 0)),
            "rv_err": 0.5,
            "v_corr": None,
            "rv2": None,
            "rv2_obs": float(orbit.rv_model(ti, 3.0, 2460000.5, 0, 270, 90, 0)),
            "rv2_err": 0.8,
        }
        for i, ti in enumerate(t)
    ]
    tab.show_rvs(rows)
    assert tab.table.item(0, 4).text() != "—" and tab._is_sb2() and tab.orbit_button.isEnabled()
    emitted = []
    tab.orbit_requested.connect(lambda i, p: emitted.append(i))
    tab.period.setValue(3.0)
    tab._orbit()
    assert "rv2" in emitted[0]
    tt, v1, e1 = (np.asarray(a, float) for a in tab._series())
    _, v2, e2 = (np.asarray(a, float) for a in tab._series(2))
    tab.show_orbit(orbit.fit_sb2(tt, v1, tt, v2, e1, e2, period=3.0))
    assert "K2" in tab.status.text()
    ax, res = tab.plot.figure.axes  # velocities with both orbits, and the residuals panel below
    assert res.get_ylabel() == "O−C (km/s)" and len(ax.get_lines()) >= 3
    from astrowb.ui.export import save_publication

    out = save_publication(tab.plot.figure, tmp_path / "orbit.pdf")
    assert out.endswith("orbit.pdf") and (tmp_path / "orbit.pdf").stat().st_size > 1000


def test_velocities_follow_the_optical_doppler_convention():
    """Spectra shift as lambda (1 + v/c): a velocity read as c * ln-shift is short by v^2 / 2c (17 m/s at 100 km/s,
    150 m/s at 300 km/s), which pulled every orbit's gamma down. Noise-free spectra: both methods within 2 m/s."""
    for v1, v2 in ((-100.0, 130.0), (250.0, -280.0)):
        r = sb2.todcor(WAVE, composite(v1, v2, snr=1e12), WAVE, T1, WAVE, T2, -350, 350)
        assert abs(r["rv1"] - v1) < 0.002, (v1, r["rv1"])
        one = rv.ccf(WAVE, template(LINES1, DEPTH1, 0.08, v1), WAVE, T1, -350, 350)
        assert abs(one["rv"] - v1) < 0.002, (v1, one["rv"])


def test_velocity_errors_are_honest():
    """The reported errors match the scatter of repeated noisy spectra (Zucker 2003 with the independent pixels and
    the full 2-D peak; before, the oversampled grid and 1-D cuts made them 1.4-1.9 times too small)."""
    rng = np.random.default_rng(21)
    rows = [sb2.todcor(WAVE, composite(40.0, -70.0, snr=60, rng=rng), WAVE, T1, WAVE, T2, -150, 150) for _ in range(16)]
    for k in ("rv1", "rv2"):
        v = np.array([r[k] for r in rows])
        assert 0.6 < v.std() / np.median([r[k + "_err"] for r in rows]) < 1.6, k
    ones = [rv.ccf(WAVE, template(LINES1, DEPTH1, 0.08, 25.0) + rng.normal(0, 0.02, len(WAVE)), WAVE, T1, -100, 100)
            for _ in range(16)]  # fmt: skip
    v = np.array([o["rv"] for o in ones])
    assert 0.6 < v.std() / np.median([o["rv_err"] for o in ones]) < 1.6


def test_one_template_for_both_stars_keeps_the_brighter_as_component_one():
    """With the same template twice, (v1, v2) and (v2, v1) fit equally and noise chose: on ten real AI Phe spectra
    the two stars swapped in three, which ruined the mass ratio (K1/K2 0.99 against 0.96)."""
    rng = np.random.default_rng(7)
    for v_bright, v_faint in ((60.0, -50.0), (-45.0, 40.0), (25.0, -30.0), (-70.0, 65.0)):
        f = (template(LINES1, DEPTH1, 0.08, v_bright) + 0.6 * template(LINES1, DEPTH1, 0.08, v_faint)) / 1.6
        r = sb2.todcor(WAVE, f + rng.normal(0, 0.01, f.size), WAVE, T1, WAVE, T1, -200, 200)
        assert r["rv1"] == pytest.approx(v_bright, abs=0.5) and r["rv2"] == pytest.approx(v_faint, abs=0.5)
        assert r["alpha"] < 1 and r["flux_ratio"] == pytest.approx(0.6, rel=0.15)


def test_a_zero_filled_gap_is_missing_data_not_a_line(tmp_path):
    """HARPS's s1d fills the gap between its CCDs with zeros: read as missing (NaN), single zeros stay."""
    from astropy.io import fits

    from astrowb.spectroscopy import spectrum_io

    flux = np.ones(500)
    flux[200:240] = 0.0  # a gap
    flux[400] = 0.0  # one saturated pixel
    h = fits.Header({"CRVAL1": 5000.0, "CDELT1": 0.01, "CRPIX1": 1.0})
    fits.PrimaryHDU(flux, h).writeto(tmp_path / "s.fits")
    _, f, _, _ = spectrum_io.read(tmp_path / "s.fits")
    assert np.isnan(f[200:240]).all() and f[400] == 0 and np.isfinite(f[:200]).all()


def test_one_smooth_template_does_not_pull_both_stars_together():
    """One finely sampled template for both stars (as with the HARPS spectrum of tau Ceti for AI Phe): next to the
    diagonal C12 -> 1 and 1 - C12^2 -> 0; that band is left out, the two velocities stay apart."""
    rng = np.random.default_rng(8)
    wave = np.arange(5000.0, 5300.0, 0.01)  # oversampled: neighbouring lags nearly identical
    lines = rng.uniform(5005, 5295, 400)
    depth = rng.uniform(0.05, 0.5, 400)

    def star(v):
        f = np.ones_like(wave)
        for c, d in zip(lines, depth, strict=True):
            f -= d * np.exp(-0.5 * ((wave - c * (1 + v / 299792.458)) / 0.06) ** 2)
        return f

    obs = (star(-33.0) + 0.6 * star(58.0)) / 1.6 + rng.normal(0, 0.005, wave.size)
    tmpl = star(0.0)
    r = sb2.todcor(wave, obs, wave, tmpl, wave, tmpl.copy(), -150, 150)
    assert abs(r["rv1"] + 33.0) < 0.5 and abs(r["rv2"] - 58.0) < 0.5 and 0.5 < r["flux_ratio"] < 0.7


def test_a_circular_double_lined_orbit_is_fitted_circular():
    # TZ For (HARPS, BF velocities): with e free, T_peri and omega are undefined on a circular orbit and their
    # covariance spoiled the rest (K errors 15 km/s, a sin i 16.7 instead of 120 R_sun)
    from astrowb.spectroscopy.orbit import fit_sb2, rv_model, sb2_dimensions

    rng = np.random.default_rng(4)
    t = np.sort(rng.uniform(0, 400, 22))
    v1 = rv_model(t, 75.66647, 10.0, 0.0, 90.0, 38.9, 18.0) + rng.normal(0, 0.6, t.size)
    v2 = rv_model(t, 75.66647, 10.0, 0.0, 270.0, 40.9, 18.0) + rng.normal(0, 3.0, t.size)
    o = fit_sb2(t, v1, t, v2, period=75.66647, fix_period=True)
    assert o["circular"] and o["e"] == 0 and o["k_err"] < 1 and o["k2_err"] < 1.5
    assert o["k"] == pytest.approx(38.9, abs=0.6) and o["k2"] == pytest.approx(40.9, abs=2)
    assert o["a_sini_rsun"] == pytest.approx(sb2_dimensions(75.66647, 0, o["k"], o["k2"])[2], rel=1e-6)
    eccentric = fit_sb2(t, v1, t, v2, period=75.66647, fix_period=True, circular=False)
    assert not eccentric["circular"]


def test_a_template_broadened_to_a_fast_rotator():
    from astrowb.spectroscopy import rv

    wave = np.exp(np.arange(np.log(5000.0), np.log(5100.0), 1 / 200000))
    sharp = 1 - 0.6 * np.exp(-0.5 * ((wave - 5050.0) / 0.03) ** 2)
    w2, broad = rv.rotate(wave, sharp, 46.0)
    depth = lambda w, f: np.trapezoid(1 - f, w)  # noqa: E731
    assert depth(w2, broad) == pytest.approx(depth(wave, sharp), rel=0.02)  # the line keeps its strength
    half = w2[broad < 1 - (1 - broad.min()) / 2]
    assert (half[-1] - half[0]) / 5050 * rv.C_KMS == pytest.approx(2 * 46 * 0.87, rel=0.2)  # ~ 80 km/s wide
    assert rv.rotate(wave, sharp, 0)[1] is sharp

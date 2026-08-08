"""Third-body light-time orbit and apsidal motion fitted to simulated minimum times with known truth."""

import numpy as np
import pytest

from astrowb.timeseries.ephemeris import Minimum
from astrowb.timeseries.oc_models import _apsidal, _tau, fit_apsidal, fit_ltte

T0, P = 2445000.3, 0.8123456


def test_ltte_recovers_the_third_body():
    rng = np.random.default_rng(4)
    e = np.sort(rng.choice(np.arange(0, 14000), 90, replace=False)).astype(float)
    truth = {"a": 0.006, "p3": 3652.5, "t3": T0 + 1000.0, "e": 0.3, "w": 120.0}
    t = T0 + P * e
    t = t + _tau(t, truth["a"], truth["p3"], truth["t3"], truth["e"], truth["w"]) + rng.normal(0, 0.0003, len(e))
    minima = [Minimum(float(x), 0.0003) for x in t]
    f = fit_ltte(minima, T0, P + 2e-7)  # a slightly wrong reference period, as in practice
    assert f.p3 == pytest.approx(truth["p3"], rel=0.03)
    assert f.amplitude == pytest.approx(truth["a"], rel=0.08) and f.e == pytest.approx(truth["e"], abs=0.08)
    assert f.period == pytest.approx(P, abs=1e-7) and f.chi2r < 1.5
    assert np.std(f.residuals) < 0.0004
    assert 0 < f.mass_function < 1  # solar masses: a plausible companion
    # one start per (e, omega) stopped in a neighbouring valley here: omega 134 deg, chi2 115 against 79
    assert f.omega == pytest.approx(truth["w"], abs=5) and np.sum((f.residuals / 0.0003) ** 2) < 90
    assert 20 < f.errors["t3"] < 60  # omega's 3.6 deg are 36 days of T3 (MCMC agrees); was 4.4


@pytest.mark.parametrize("ecc, w", [(0.05, 30.0), (0.6, 250.0), (0.8, 300.0)])
def test_ltte_finds_eccentric_orbits_at_any_orientation(ecc, w):
    rng = np.random.default_rng(1)
    e = np.sort(rng.choice(np.arange(0, 14000), 90, replace=False)).astype(float)
    t = T0 + P * e
    t = t + _tau(t, 0.006, 3652.5, T0 + 1000.0, ecc, w) + rng.normal(0, 0.0003, len(e))
    f = fit_ltte([Minimum(float(x), 0.0003) for x in t], T0, P)
    assert f.e == pytest.approx(ecc, abs=0.05) and f.chi2r < 1.3
    if ecc > 0.3:
        assert abs((f.omega - w + 180) % 360 - 180) < 8


def test_mcmc_intervals_hold_the_truth():
    rng = np.random.default_rng(4)
    e = np.sort(rng.choice(np.arange(0, 14000), 90, replace=False)).astype(float)
    t = T0 + P * e
    t = t + _tau(t, 0.006, 3652.5, T0 + 1000.0, 0.3, 120.0) + rng.normal(0, 0.0003, len(e))
    f = fit_ltte([Minimum(float(x), 0.0003) for x in t], T0, P + 2e-7, mcmc_steps=800)
    post = f.mcmc["params"]
    assert 0.2 < f.mcmc["acceptance"] < 0.7 and {"e", "omega", "f_m3"} <= set(post)
    for name, true in (("amplitude", 0.006), ("p3", 3652.5), ("e", 0.3), ("omega", 120.0)):
        mid, lo, hi = post[name]
        assert mid - 3 * lo < true < mid + 3 * hi, name
    assert f.errors["e"] == max(post["e"][1:])  # the table shows the larger side


def test_apsidal_motion_recovers_omega_dot():
    rng = np.random.default_rng(6)
    ps, ecc, w0, dw = 2.5, 0.05, 60.0, 0.1  # U = 3600 cycles = 24.6 years
    e1 = np.sort(rng.choice(np.arange(0, 3000), 40, replace=False)).astype(float)
    e2 = np.sort(rng.choice(np.arange(0, 3000), 40, replace=False)).astype(float)
    kinds = np.array(["I"] * 40 + ["II"] * 40)
    e_int = np.concatenate([e1, e2])
    t = _apsidal(e_int, kinds, T0, ps, ecc, w0, dw) + rng.normal(0, 0.0002, 80)
    minima = [Minimum(float(x), 0.0002, k) for x, k in zip(t, kinds, strict=True)]
    f = fit_apsidal(minima, T0, ps)
    assert f.d_omega == pytest.approx(dw, rel=0.05) and f.e == pytest.approx(ecc, abs=0.003)
    assert f.u_years == pytest.approx(360 / dw * ps / 365.25, rel=0.05) and f.chi2r < 1.5
    with pytest.raises(ValueError, match="secondary"):
        fit_apsidal(minima[:40], T0, ps)


def test_oc_page_fits_both_models(qtbot):
    from astrowb.ui.workspaces import OCPage

    page = OCPage()
    qtbot.addWidget(page)
    rng = np.random.default_rng(6)
    ps = 2.5
    e = np.arange(0, 3000, 75.0)
    kinds = np.array(["I", "II"] * (len(e) // 2))
    t = _apsidal(e, kinds, T0, ps, 0.05, 60.0, 0.1) + rng.normal(0, 0.0002, len(e))
    page.text.setPlainText("\n".join(f"{x:.6f} 0.0002 {k}" for x, k in zip(t, kinds, strict=True)))
    page.t0.setText(str(T0))
    page.period.setText(str(ps))
    page.apsidal.setChecked(True)
    f = page.run_fit()
    assert f.d_omega == pytest.approx(0.1, rel=0.1) and page.result.text().startswith("Apsidal motion:")
    page.use_mcmc.setChecked(True)
    page.mcmc_steps.setValue(200)
    f = page.run_fit()
    assert f.mcmc and "MCMC" in page.result.text() and page.fit_table()[0][2][2] is not None  # e has an error
    page.ltte.setChecked(True)
    assert page.run_fit() is not None and page.result.text().startswith("Third body:")
    page.text.setPlainText(f"{T0:.5f} 0.001 I")
    assert page.run_fit() is None and "8 minima" in page.result.text()
    page.linear.setChecked(True)
    assert not page.use_mcmc.isEnabled()  # a linear problem: least squares are exact


def test_mcmc_runs_as_a_task_and_reports_progress(qtbot):
    from astrowb.timeseries.steps import oc_fit_step
    from astrowb.ui.workspaces import OCPage

    rng = np.random.default_rng(6)
    ps, e = 2.5, np.arange(0, 3000, 75.0)
    kinds = np.array(["I", "II"] * (len(e) // 2))
    t = _apsidal(e, kinds, T0, ps, 0.05, 60.0, 0.1) + rng.normal(0, 0.0002, len(e))
    text = "\n".join(f"{x:.6f} 0.0002 {k}" for x, k in zip(t, kinds, strict=True))
    page = OCPage()
    qtbot.addWidget(page)
    calls = []
    page.background = lambda *args: calls.append(args)
    page.text.setPlainText(text)
    page.t0.setText(str(T0))
    page.period.setText(str(ps))
    page.apsidal.setChecked(True)
    page.use_mcmc.setChecked(True)
    page.mcmc_steps.setValue(200)
    assert page.run_fit() is None and calls[0][:2] == ("apsidal", text) and calls[0][4] == 200

    class Ctx:
        seen = []

        def progress(self, f, word=""):
            self.seen.append(word)

        def check(self):
            pass

    ctx = Ctx()
    params = {"model": "apsidal", "t0": T0, "period": ps, "mcmc_steps": 200}
    fit = oc_fit_step({"minima": text}, params, ctx)["fit"]
    assert fit.mcmc and "MCMC" in ctx.seen
    page.show_fit(fit, calls[0][5])  # the task's answer drawn on the page
    assert "MCMC" in page.result.text() and page.fit_result is fit

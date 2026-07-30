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
    page.ltte.setChecked(True)
    assert page.run_fit() is not None and page.result.text().startswith("Third body:")
    page.text.setPlainText(f"{T0:.5f} 0.001 I")
    assert page.run_fit() is None and "8 minima" in page.result.text()

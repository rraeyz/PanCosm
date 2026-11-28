"""OC-5, OC-9, OC-11: the Models and Periodogram tabs and the Applegate check of the O−C window; synthetic minima."""

import numpy as np
import pytest

T0, P, P3, A = 2455000.0, 0.5, 3000.0, 0.005


def _window(qtbot, tmp_path, times):
    from astrowb.settings import Settings
    from astrowb.ui.main_window import MainWindow

    window = MainWindow(Settings(tmp_path))
    qtbot.addWidget(window)
    win = window.open_area("oc")
    page = window.oc_page
    page.text.setPlainText("\n".join(f"{t:.6f} 0.0003 I" for t in times))
    page.period.setText(str(P))
    page.t0.setText(str(T0))
    return win, page


def _ltte_times(seed=2):
    from astrowb.timeseries.oc_models import _tau

    rng = np.random.default_rng(seed)
    e = np.sort(rng.choice(np.arange(0, 9000), 60, replace=False)).astype(float)
    t = T0 + P * e
    return t + _tau(t, A, P3, T0 + 700.0, 0.3, 60.0) + rng.normal(0, 0.0003, e.size)


def test_the_highest_residual_peak_seeds_a_third_body_fit_that_recovers_its_period(qtbot, tmp_path):
    win, page = _window(qtbot, tmp_path, _ltte_times())
    assert "result_periodogram" not in win.docks and not page.peak_button.isEnabled()  # added at the first fit
    assert page.run_fit() is not None  # linear: the wave is left in the residuals
    assert page.peak_period == pytest.approx(P3, rel=0.1) and page.peak_button.isEnabled()
    assert "result_periodogram" in win.docks
    page.peak_button.click()
    f = page.fit_result
    assert page.ltte.isChecked() and hasattr(f, "p3")
    assert f.p3 == pytest.approx(P3, abs=3 * f.errors["p3"]) and f.amplitude == pytest.approx(A, rel=0.15)


def test_the_models_tab_ranks_a_parabola_first_and_gives_its_dp_dt(qtbot, tmp_path):
    rng = np.random.default_rng(4)
    e = np.sort(rng.choice(np.arange(0, 20000), 40, replace=False)).astype(float)
    win, page = _window(qtbot, tmp_path, T0 + P * e + 2e-10 * e**2 + rng.normal(0, 0.0003, e.size))
    assert "result_models" not in win.docks
    found = page.compare_button.click() or page.compared
    assert "result_models" in win.docks
    assert set(found) == {"linear", "quadratic", "cubic", "segmented", "sinusoid", "damped"}
    view = page.models_view
    assert view.table.model().rowCount() == 6
    first = page.models_label.text().splitlines()[0]
    assert first.startswith("quadratic is preferred") or first.startswith("cubic is preferred")
    from astrowb.timeseries.ephemeris_models import dp_dt

    rate, err, _ = dp_dt(found["quadratic"])
    assert rate == pytest.approx(2 * 2e-10 / P * 365.25 * 86400, abs=3 * err)
    assert "Min I = BJD_TDB" in page.models_label.text()
    page.weights.setCurrentIndex(1)  # no methods in the rows: every weight 1, the same ranking
    page.compare_button.click()
    assert page.compared["quadratic"]["bic"] == pytest.approx(found["quadratic"]["bic"], rel=1e-6)


def test_too_few_minima_for_the_comparison_are_said(qtbot, tmp_path):
    win, page = _window(qtbot, tmp_path, [T0 + P * k for k in range(5)])
    page.compare_button.click()
    assert "8" in page.models_label.text() and page.compared is None


def test_the_applegate_check_uses_the_third_body_term(qtbot, tmp_path):
    from astrowb.timeseries.applegate import dp_over_p, energy
    from astrowb.ui.oc_applegate import dialog

    win, page = _window(qtbot, tmp_path, _ltte_times())
    assert "compare the models" in dialog(page).result.text()
    page.ltte.setChecked(True)
    f = page.run_fit()
    d = dialog(page)
    for box, v in zip(d.values, (0.4, 0.4, 3500.0, 0.03, 2.0), strict=True):
        box.setValue(v)
    k, p_mod = f.amplitude * 86400.0, f.p3 / 365.25
    out = energy(0.4, 0.4, 3500.0, 0.03, 2.0, f.period, dp_over_p(k, p_mod), p_mod)
    assert f"{out['tian']:.3g} (Tian" in d.result.text() and f"A = {out['A']:.3g}" in d.result.text()


def test_the_guides_case_the_practice_minima_peak_near_2900_days(qtbot, tmp_path):
    from astrowb import sampledata

    win, page = _window(qtbot, tmp_path, [])
    page.text.setPlainText(sampledata.minima(tmp_path).read_text())
    page.t0.setText(str(sampledata.LTTE["t0"]))
    page.period.setText(str(sampledata.LTTE["period"]))
    page.run_fit()
    assert page.peak_period == pytest.approx(2900, rel=0.05)
    page.peak_button.click()
    assert page.fit_result.p3 == pytest.approx(2900, rel=0.05)

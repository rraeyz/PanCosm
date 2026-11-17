"""UI-16.5: the correlation matrix of an O−C fit and the Correlations tab; synthetic data."""

import numpy as np
import pytest

from astrowb.timeseries.ephemeris import Minimum, fit
from astrowb.timeseries.oc_uncertainty import correlation_dict


def test_linear_ephemeris_correlation_is_the_analytic_one():
    e = np.array([0, 1, 2, 3, 5, 8, 13, 21, 34, 40], float)  # a known epoch distribution
    minima = [Minimum(2455000.0 + 2.5 * k + 1e-4 * np.sin(k), 0.001, "I") for k in e]
    f = fit(minima, 2455000.0, 2.5)
    assert f.correlation["names"] == ["T0", "P"]
    m = np.array(f.correlation["matrix"])
    expected = -e.mean() / np.sqrt((e**2).mean())  # equal weights, T0 at E = 0
    assert m[0, 1] == pytest.approx(expected, abs=1e-6) and m[1, 1] == pytest.approx(1.0)
    assert np.allclose(m, m.T)


def test_samples_correlation_leaves_out_constant_columns():
    rng = np.random.default_rng(3)
    a = rng.normal(size=5000)
    got = correlation_dict(["a", "b", "c"], samples={"a": a, "b": a + 0.1 * rng.normal(size=5000), "c": np.ones(5000)})
    assert got["names"] == ["a", "b"] and got["matrix"][0][1] > 0.9


def test_the_correlations_tab_appears_at_the_first_fit_and_marks_tied_pairs(qtbot, tmp_path):
    from astrowb.settings import Settings
    from astrowb.ui.main_window import MainWindow

    window = MainWindow(Settings(tmp_path))
    qtbot.addWidget(window)
    win = window.open_area("oc")
    page = window.oc_page
    assert "result_correlations" not in win.docks
    page.text.setPlainText("\n".join(f"{2455000.0 + 0.5 * k:.6f} 0.0003 I" for k in range(81, 120, 2)))
    page.period.setText("0.5")
    page.t0.setText("2455000.0")
    assert page.run_fit() is not None
    table = page.correlations_view.table
    assert table.rowCount() == 2 and table.columnCount() == 3
    assert "tied" in table.item(0, 2).toolTip()
    assert table.item(0, 1).toolTip() == ""  # the diagonal is not marked
    page.period.setText("0.51")
    assert "(out of date)" in win.docks["result_correlations"].windowTitle()
    window.engine.shutdown()

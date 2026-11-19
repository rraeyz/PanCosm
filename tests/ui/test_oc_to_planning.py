"""OC-5: the O−C fit's ephemeris, at the latest epoch, becomes a Planning target; synthetic minima."""

import pytest

from astrowb.timeseries.ephemeris_models import updated


@pytest.fixture
def window(qtbot, tmp_path):
    from astrowb.settings import Settings
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    yield win
    win.engine.shutdown()


@pytest.fixture
def oc(window):
    window.open_area("oc")
    page = window.oc_page
    page.text.setPlainText(
        "\n".join(
            f"{2455000.0 + 1.5 * (k + (0.5 if k == 3 else 0)) + 1e-6 * k * k:.6f} 0.0003 {'II' if k == 3 else 'I'}"
            for k in range(20)
        )
    )
    page.period.setText("1.5")
    page.t0.setText("2455000.0")
    page.star.setText("Test Star")
    return window, page


def test_button_is_disabled_before_a_fit_and_sends_the_updated_ephemeris(oc):
    window, page = oc
    assert not page.to_planning.isEnabled()
    page.quadratic.setChecked(True)
    f = page.run_fit()
    assert page.to_planning.isEnabled()
    got = []
    window.run_step_for = lambda area, step, inputs, params=None, on_done=None, on_fail=None: (
        got.append(inputs["name"]),
        on_done({"target": {"name": "Test Star", "ra": 10.0, "dec": 20.0}}),
    )
    n = window.plan_page.table.rowCount()
    page.to_planning.click()
    t = window.plan_page.targets()[-1]
    k = f.order + 1
    import numpy as np

    sd = np.array([f.t0_err, f.period_err, f.q_err])[:k]
    cov = np.array(f.correlation["matrix"]) * np.outer(sd, sd)
    t0, _, p, _, _ = updated({"epochs": f.epochs, "order": 2, "coef": [f.t0, f.period, f.q], "cov": cov}, at="latest")
    assert window.plan_page.table.rowCount() == n + 1 and got == ["Test Star"]
    assert abs(t["t0"] - t0) < 1e-9 and abs(t["period"] - p) < 1e-9 and t["secondary"]
    assert abs(p - f.period) > 1e-9  # the instantaneous period at the latest epoch, not the epoch-0 one


def test_a_missing_name_is_said_in_the_result_line(oc):
    window, page = oc
    page.run_fit()
    page.star.clear()
    page.to_planning.click()
    assert "name" in page.result.text()

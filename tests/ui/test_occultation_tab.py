import numpy as np
import pytest

from astrowb.settings import Settings


@pytest.fixture
def tab(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    yield win.lightcurve_page.occultation_tab
    win.engine.shutdown()


def _box_csv(path, d0=3.013, r0=5.413, dt=0.04):
    t = np.arange(200) * dt
    f = np.clip(np.minimum(r0, t + dt / 2) - np.maximum(d0, t - dt / 2), 0, None) / dt
    y = 1 - 0.9 * f + np.random.default_rng(5).normal(0, 0.1, len(t))
    path.write_text("time,flux\n" + "\n".join(f"{a},{b}" for a, b in zip(t, y, strict=True)))


def test_fit_recovers_the_times_within_their_errors(tab, qtbot, tmp_path):
    p = tmp_path / "occ.csv"
    _box_csv(p)
    tab._load(str(p))
    assert len(tab.time) == 200
    tab.fit_button.click()
    qtbot.waitUntil(lambda: tab.result is not None, timeout=60000)
    r = tab.result
    assert abs(r["D"] - 3.013) < 3 * r["D_err"] + 0.02 and abs(r["R"] - 5.413) < 3 * r["R_err"] + 0.02
    assert tab.table.model.rowCount() >= 4
    assert [s.name for s in tab.plot.figure.panels[0].series] == ["light curve", "model"]


def test_failures_are_said_not_raised(tab, tmp_path):
    tab._fit()
    assert "Load a light curve" in tab.status.text()
    bad = tmp_path / "bad.csv"
    bad.write_text("only\n")
    tab._load(str(bad))
    assert "Cannot read bad.csv" in tab.status.text()
    tab._load(str(tmp_path / "missing.csv"))
    assert "Cannot read missing.csv" in tab.status.text()
    tab.time, tab.flux = [0.0, 1.0], [1.0, 1.0]  # too short for the fit: the step fails with a message
    tab.show_error("an occultation fit needs matching times and flux, at least 6 points")
    assert tab.status.text()

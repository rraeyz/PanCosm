"""UI-16.7: the Exoplanets window's Chains, Corner and Report tabs and the convergence lines."""

import numpy as np
import pytest

from astrowb.occult.model import transit
from astrowb.photometry import lcfile
from astrowb.photometry import transitfit as tf
from astrowb.settings import Settings
from astrowb.ui import exoplanets_docks as docks

P, TC, K, A, B = 1.42, 2459500.6123, 0.145, 6.3, 0.5


def test_convergence_lines_warn_on_rhat_or_ess():
    m = {"names": ["a", "b"], "rhat": {"a": 1.001, "b": 1.05}, "ess_bulk": {"a": 900.0, "b": 900.0}}
    lines = docks.convergence_lines(m)
    assert len(lines) == 3 and lines[2].startswith("Warning") and "(b)" in lines[2]
    m["rhat"]["b"], m["ess_bulk"]["a"] = 1.0, 100.0
    assert "(a)" in docks.convergence_lines(m)[2]
    m["ess_bulk"]["a"] = 900.0
    assert len(docks.convergence_lines(m)) == 2 and docks.convergence_lines(None) == []


def test_the_chain_tabs_fill_after_an_mcmc_fit(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    rng = np.random.default_rng(3)
    t = np.linspace(TC - 0.12, TC + 0.12, 120)
    f = transit(t - TC, P, 0.0, K, A, np.degrees(np.arccos(B / A)), "quadratic", (0.4, 0.2))
    lc = {"time": t.tolist(), "rel_flux": (f + rng.normal(0, 0.0015, t.size)).tolist(),
          "rel_flux_err": [0.0015] * t.size, "time_scale": "BJD_TDB"}  # fmt: skip
    lcfile.write(lc, tmp_path / "n.lc.ecsv")
    start = {"tc": TC + 0.002, "k": 0.13, "a_rs": 6.0, "b": 0.4, "u1": 0.4, "u2": 0.2}
    out = tf.fit(t, lc["rel_flux"], lc["rel_flux_err"], P, start, mcmc_steps=400)
    win_main = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win_main)
    try:
        win = win_main.open_area("exoplanets")
        page = win_main.exoplanets_page
        assert not {"result_chains", "result_corner", "result_report"} & set(win.docks)  # docked at the first fit
        page.add_files([str(tmp_path / "n.lc.ecsv")])
        page.show_fit(out)
        assert {"result_chains", "result_corner", "result_report"} <= set(win.docks)
        text = page.report_view.toPlainText()
        assert text.startswith("Mid-transit") and "R-hat" in text
        assert pytest.approx(out["mcmc"]["rhat"]["k"], abs=1e-3) == float(text.split("k: R-hat ")[1].split(",")[0])
        assert len(page.corner_canvas.figure.axes) == len(out["mcmc"]["names"]) ** 2
        assert page.chains_plot.failed in (None, "", False)
    finally:
        win_main.engine.shutdown()

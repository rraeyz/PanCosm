"""PHO-26: the eclipse timing methods are a choice in the Timing stage, and Compare methods tables them."""

import numpy as np
import pytest

from astrowb.ui.photometry_minimum_methods import method_names
from astrowb.ui.photometry_page import PhotometryPage

T = 2461000.4


def _lc(n=240):
    t = np.linspace(T - 0.08, T + 0.08, n)
    y = 1 - 0.3 * np.exp(-0.5 * ((t - T) / 0.02) ** 2) + np.random.default_rng(1).normal(0, 0.003, n)
    return {"time": t.tolist(), "rel_flux": y.tolist(), "rel_flux_err": [0.003] * n, "time_scale": "BJD_TDB"}


def test_each_eclipse_method_is_sent_and_named(qtbot):
    page = PhotometryPage()
    qtbot.addWidget(page)
    sent = []
    page.minimum_requested.connect(lambda lc, params: sent.append(params["method"]))
    page.light_curve = _lc()
    assert page.kvw_method.currentData() == "kvw" and page.kvw_method.isEnabled()
    for i in range(page.kvw_method.count()):
        page.kvw_method.setCurrentIndex(i)
        assert page.kvw_method.itemData(i, 3)
        page._minimum()
        page.show_minimum({"time": T, "error": 0.001, "time_scale": "BJD_TDB", "method": sent[-1]})
        assert method_names()[sent[-1]] in page.result.text()
    assert sent == ["kvw", "mikulasek", "polynomial", "gaussian", "lorentzian", "bisector"]
    page.trapezoid.setChecked(True)
    assert not page.kvw_method.isEnabled()
    page._minimum()
    assert sent[-1] == "trapezoid"


def test_compare_methods_gives_a_row_per_method_within_errors(qtbot):
    from astrowb.photometry.compare_step import compare_minimum_methods_step

    page = PhotometryPage()
    qtbot.addWidget(page)
    got = []
    page.minimum_requested.connect(lambda lc, params: got.append(params))
    page.light_curve = _lc()
    page.compare_button.setEnabled(True)
    page.compare_button.click()
    assert got == [{"compare": True}]
    from astrowb.ui.photometry_minimum_methods import show_comparison

    c = compare_minimum_methods_step({"light_curve": page.light_curve}, {}, None)["comparison"]
    show_comparison(page, c)
    assert page.compare_table.model.rowCount() == len(c["rows"]) == 6
    for r in c["rows"]:
        assert abs(r["time"] - T) < 3 * r["error"], r["method"]
    assert page.compare_table.model.index(0, 3).data() == "+0.0"


def test_compare_methods_refuses_a_curve_without_an_eclipse():
    from astrowb.photometry.compare_step import compare_minimum_methods_step

    flat = {"time": np.linspace(0, 1, 100).tolist(), "rel_flux": [1.0] * 100}
    with pytest.raises(ValueError):
        compare_minimum_methods_step({"light_curve": flat}, {}, None)

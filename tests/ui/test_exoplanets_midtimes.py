"""UI-16.7: the Exoplanets window's Mid-times tab: the session list, the linear ephemeris and the O−C points."""

import numpy as np
import pytest
from PySide6.QtWidgets import QWidget

from astrowb.ui.exoplanets_midtimes import ephemeris_fit, midtimes, midtimes_dock, oc_figure, tc_header
from astrowb.ui.exoplanets_page import ExoplanetsPage

T0, P, SIGMA = 2459500.5, 1.4200242, 0.0003
EPOCHS = [0, 3, 4, 9, 12]


class FakeWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.tabs = {}

    def add_result_tab(self, key, title, widget):
        self.tabs[key] = widget


def test_midtimes_tab_lists_fits_and_fits_the_ephemeris(qtbot):
    rng = np.random.default_rng(5)
    page = ExoplanetsPage()
    qtbot.addWidget(page)
    page.period.setValue(P)
    page.sets = [(f"n{i}.lc.ecsv", {}) for i in range(len(EPOCHS))]
    win = FakeWindow()
    qtbot.addWidget(win)
    page.show_fit = lambda out: None  # the transit plot is not under test
    midtimes_dock(win, page)
    assert "midtimes" not in win.tabs  # docked at the first fit
    sent = []
    page.midtimes_to_oc.connect(sent.append)
    for i, e in enumerate(EPOCHS):
        page.current = i
        tc = T0 + e * P + rng.normal(0, SIGMA)
        page.fits[i] = {"values": {"tc": tc}, "errors": {"tc": SIGMA}}
        page.show_fit({})
        assert page.midtimes_table.table.rowCount() == i + 1
    assert "midtimes" in win.tabs
    rows = midtimes(page)
    assert [r[0] for r in rows] == [f"n{i}.lc.ecsv" for i in range(5)]
    text = page.midtimes_summary.text()
    p_fit, p_err = (
        float(text.split("P = ")[1].split(" ± ")[0]),
        float(text.split("P = ")[1].split(" ± ")[1].split(" d")[0]),
    )
    assert abs(p_fit - P) < 3 * p_err and p_err < 1e-4
    s = oc_figure(ephemeris_fit(rows, P)).panels[0].series[0]  # the O−C points: epochs and minutes
    assert list(s.x) == EPOCHS and np.all(np.abs(s.y) < 5 * SIGMA * 1440)
    page.midtimes_send.click()
    assert sent == [rows]


def test_one_fit_gives_no_ephemeris(qtbot):
    assert ephemeris_fit([("a", T0, SIGMA)], P) is None
    assert ephemeris_fit([("a", T0, SIGMA), ("b", T0 + 0.01, SIGMA)], P) is None  # the same epoch
    f = ephemeris_fit([("a", T0, SIGMA), ("b", T0 + 5 * P, SIGMA)], P)
    assert f.period == pytest.approx(P, abs=1e-9)
    s = oc_figure(f).panels[0].series[0]
    assert len(s.x) == 2 and np.allclose(s.y, 0, atol=1e-6)


def test_tc_header_names_the_scale_the_files_state(qtbot):
    page = ExoplanetsPage()
    qtbot.addWidget(page)
    page.sets = [
        ("a", {"time_scale": "BJD_TDB"}),
        ("b", {"time_scale": "BJD_TDB"}),
        ("c", {}),
        ("d", {"time_scale": "JD_UTC"}),
    ]
    page.fits = {0: {}, 1: {}}
    assert tc_header(page) == "Tc (BJD_TDB)"
    page.fits = {0: {}, 3: {}}  # two scales
    assert tc_header(page) == "Tc (BJD)"
    page.fits = {0: {}, 2: {}}  # one file states none
    assert tc_header(page) == "Tc (BJD)"

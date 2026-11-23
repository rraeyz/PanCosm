"""PER-W accept: star name -> download -> search -> click a peak -> folded curve, in at most four actions (the name is
typed and Enter downloads, then Search and a click on the peak's row in the Peaks inspector). The download is
answered in the test, never by MAST: a synthetic curve with a 0.7 d and a weaker 2.3 d signal; the click on the 2.3 d
peak folds there."""

import numpy as np
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from astrowb.ui.kit.table import TableView

CLICKS = ("click ", "choose ", "menu ")


def test_name_to_folded_curve_in_four_clicks(walk):
    h = walk("en")
    h.area("timeseries")
    pp = h.page.period_page
    t = np.sort(np.random.default_rng(3).uniform(0, 30, 900))
    flux = 1 + 0.01 * np.sin(2 * np.pi * t / 0.7) + 0.006 * np.sin(2 * np.pi * t / 2.3)
    lc = {"time": t.tolist(), "rel_flux": flux.tolist(), "source": "TESS"}

    def answered(area, step, inputs, params, on_done=None, on_fail=None):  # the archive's answer, here
        assert step == "timeseries.mission_lc" and inputs["target"] == "NY Vir"
        on_done({"light_curve": lc})

    h.main.run_step_for = answered
    h.type("period_page.archive_target", "NY Vir")  # 1: Enter starts the download
    h.wait(lambda: len(pp.time) == len(t))
    h.click("period_page.search_button")  # 2
    h.wait(lambda: getattr(pp, "periodogram", None) is not None)
    assert pp.best == pytest.approx(0.7, rel=0.01)
    peaks = next(
        v for v in h.window.findChildren(TableView) if v.model.table is not None and "period" in v.model.table.colnames
    )
    row = int(np.argmin(np.abs(np.asarray(peaks.model.table["period"], float) - 2.3)))
    pos = peaks.view.visualRect(peaks.model.index(row, 0)).center()
    h._act("click peak row", lambda: QTest.mouseClick(peaks.view.viewport(), Qt.LeftButton, pos=pos), 2.0)  # 3
    h.wait(lambda: abs(pp.best - 2.3) < 0.05)
    h.check()
    assert pp.best == pytest.approx(2.3, rel=0.02) and "clicked peak" in pp.result.text()
    assert sum(t[0].startswith(("type ", *CLICKS)) for t in h.timings) <= 4, h.timings

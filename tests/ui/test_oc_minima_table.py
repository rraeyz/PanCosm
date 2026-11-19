"""UI-16.5: the editable minima table of the O−C window; synthetic minima."""

from PySide6.QtCore import Qt

from astrowb.ui.oc_minima_table import as_text, minima_for_fit
from astrowb.ui.oc_page import OCPage

TEXT = "2455000.0 0.001 I lit\n2455010.0 0.002 II lit\n2455020.0 0.001 I this work\n"


def test_paste_fills_the_table_and_use_and_weight_reach_the_fit(qtbot):
    page = OCPage()
    qtbot.addWidget(page)
    page.text.setPlainText(TEXT)
    t = page.minima_input
    assert t.rowCount() == 3 and t.item(1, 3).text() == "II"
    assert [m.time for m in minima_for_fit(page)] == [2455000.0, 2455010.0, 2455020.0]
    t.item(1, 0).setCheckState(Qt.Unchecked)  # unticked: left out
    t.item(2, 5).setText("4")  # weight 4: the error is halved
    got = minima_for_fit(page)
    assert [m.time for m in got] == [2455000.0, 2455020.0]
    assert got[1].error == 0.0005 and got[0].error == 0.001
    page.text.appendPlainText("2455030.0 0.001 I")  # new text keeps what was set for the old times
    assert t.rowCount() == 4 and t.item(1, 0).checkState() == Qt.Unchecked and t.item(2, 5).text() == "4"


def test_the_fit_reads_the_table(qtbot):
    page = OCPage()
    qtbot.addWidget(page)
    page.text.setPlainText("\n".join(f"{2455000 + 2.5 * k} 0.001 I" for k in range(6)))
    page.period.setText("2.5")
    page.minima_input.item(0, 0).setCheckState(Qt.Unchecked)
    page.run_fit()
    assert len(page.fit_minima) == 5


METHODS = (
    "2455000.0 0.001 I CCD lit\n2455010.0 0.002 II vis\n2455020.0 0.002 I PG x\n2455030.0 0.001 Visual\n"
    "2455040.0 0.001 I photoelectric\n2455050.0 0.001 I abc\n"
)


def test_methods_parse_show_stay_and_weight_the_fit(qtbot):
    from astrowb.timeseries.ephemeris import parse_minima

    got = parse_minima(METHODS)
    assert [m.method for m in got] == ["CCD", "vis", "pg", "vis", "pe", None]
    assert got[0].source == "lit" and got[5].source == "abc"
    page = OCPage()
    qtbot.addWidget(page)
    page.text.setPlainText(METHODS)
    t = page.minima_input
    assert [t.item(r, 6).text() for r in range(6)] == ["CCD", "vis", "pg", "vis", "pe", ""]
    t.item(5, 6).setText("pg")  # edited; kept when the text changes
    page.text.appendPlainText("2455060.0 0.001 I")
    assert t.item(5, 6).text() == "pg" and t.item(6, 6).text() == ""
    assert [m.error for m in minima_for_fit(page)][:3] == [0.001, 0.002, 0.002]
    page.weight_by_method.setChecked(True)  # vis 1, pg 3, electronic 10; no method: as before
    errs = [m.error for m in minima_for_fit(page)]
    assert errs[0] == 0.001 / 10**0.5 and errs[1] == 0.002 and errs[2] == 0.002 / 3**0.5 and errs[6] == 0.001
    assert "CCD" in as_text(parse_minima(METHODS)).splitlines()[0]
    assert [m.method for m in parse_minima(as_text(parse_minima(METHODS)))] == [m.method for m in parse_minima(METHODS)]


def test_the_diagram_has_a_series_per_kind_and_method_present(qtbot):
    page = OCPage()
    qtbot.addWidget(page)
    page.period.setText("10")
    page.text.setPlainText(METHODS)
    page.run_fit()
    names = [s.name for s in page.plot.figure.panels[0].series if s.kind == "points"]
    assert names == ["primary · CCD", "primary · vis", "secondary · vis", "primary · pg", "primary · pe", "primary"]
    page.text.setPlainText("\n".join(f"{2456000 + 10 * k} 0.001 {'I' if k % 2 else 'II'}" for k in range(6)))
    page.run_fit()
    assert [s.name for s in page.plot.figure.panels[0].series if s.kind == "points"] == ["primary", "secondary"]

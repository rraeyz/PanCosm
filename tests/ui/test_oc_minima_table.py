"""UI-16.5: the editable minima table of the O−C window; synthetic minima."""

from PySide6.QtCore import Qt

from astrowb.ui.oc_minima_table import minima_for_fit
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

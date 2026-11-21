"""UI-16.5: the count line and the time-standard line of the Minima stage; synthetic minima."""

from astrowb.ui.oc_page import OCPage

BODY = "2455000.0 0.001 I\n2455010.0 0.002 II\n2455020.0 0.001 I\n"


def _page(qtbot, text):
    page = OCPage()
    qtbot.addWidget(page)
    page.text.setPlainText(text)
    return page


def test_counts_follow_the_text(qtbot):
    page = _page(qtbot, BODY)
    assert page.minima_count.text() == "3 minima · 2 primary · 1 secondary"
    page.text.appendPlainText("2455030.0 0.001 II")
    assert page.minima_count.text() == "4 minima · 2 primary · 2 secondary"


def test_assumed_and_unstated_show_the_warning_stated_does_not(qtbot):
    page = _page(qtbot, "HJD\n" + BODY)
    assert "HJD (UTC assumed) ⚠" in page.minima_standard.text() and page.minima_standard.toolTip()
    page.text.setPlainText("HJD_TT\n" + BODY)
    assert "HJD_TT" in page.minima_standard.text() and "⚠" not in page.minima_standard.text()
    assert page.minima_standard.toolTip() == ""
    page.text.setPlainText(BODY)
    assert "not stated ⚠" in page.minima_standard.text() and page.minima_standard.toolTip()

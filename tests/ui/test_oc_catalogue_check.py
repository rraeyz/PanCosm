"""OC-14: the catalogue check button of the Minima/ephemeris stage; synthetic minima."""

from astrowb.ui.oc_catalogue_check import add_catalogue_check
from astrowb.ui.oc_page import OCPage

T0, P = 2455000.0, 0.5


def _page(qtbot):
    page = OCPage()
    qtbot.addWidget(page)
    add_catalogue_check(page)
    return page


def test_button_needs_lookup_and_minima_then_shows_the_line(qtbot):
    page = _page(qtbot)
    assert not page.catalogue_button.isEnabled() and page.catalogue_button.toolTip()
    body = "\n".join(f"{T0 + c * (P + 1e-6) + 0.0005:.6f} 0.0001 I" for c in range(3000, 3012))
    page.text.setPlainText(body)
    assert not page.catalogue_button.isEnabled()
    page.set_ephemeris({"name": "X", "t0": T0, "period": P})
    assert page.catalogue_button.isEnabled()
    page.t0.setText("1.0")  # the user's edit does not touch the catalogue values
    page.catalogue_button.click()
    text = page.catalogue_line.text()
    assert "Newest 10 minima" in text and "min a year" in text and "shifted" in text

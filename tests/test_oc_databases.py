"""OC-4: the O−C window's "From databases…" dialog; the services' answers are made in the test, never fetched."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from astrowb.timeseries.minima_table import record


@pytest.fixture
def window(qtbot, tmp_path):
    from astrowb.settings import Settings
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    win.open_area("oc")
    yield win
    win.engine.shutdown()


def _rows():
    return [record(2455000.0 + 0.5 * k, 0.0001, "II" if k % 2 else "I", "BJD_TDB", "space",
                   bjd_tdb=2455000.0 + 0.5 * k, source="Villanova Kepler EB catalogue (Conroy et al. 2014)")
            for k in range(6)]  # fmt: skip


def _dialog(window):
    from astrowb.ui.oc_databases import open_dialog

    return open_dialog(window.oc_page, window)


def test_villanova_fetch_adds_rows_with_source_and_not_twice(window):
    page = window.oc_page
    page.star.setText("KIC 7938468")
    asked = []

    def answered(area, step, inputs, params=None, on_done=None, on_fail=None):
        asked.append((step, inputs))
        on_done({"minima": _rows()})

    window.run_step_for = answered
    d = _dialog(window)
    assert d.kic.text() == "7938468"
    QTest.mouseClick(d.villanova, Qt.LeftButton)
    assert asked == [("timeseries.villanova_minima", {"kic": 7938468})]
    t = page.minima_input
    assert t.rowCount() == 6 and all("Villanova" in t.item(r, 4).text() for r in range(6))
    assert "6 minima added from Villanova" in d.status.text()
    QTest.mouseClick(d.villanova, Qt.LeftButton)  # the same star again: nothing doubled
    assert t.rowCount() == 6 and "0 minima added" in d.status.text() and "6 were already" in d.status.text()


def test_a_failed_fetch_shows_the_translated_message(window):
    window.run_step_for = lambda area, step, inputs, params=None, on_done=None, on_fail=None: on_fail(
        "no eclipse timing variations for KIC 12644769 in the Villanova catalogue"
    )
    d = _dialog(window)
    d.kic.setText("12644769")
    QTest.mouseClick(d.villanova, Qt.LeftButton)
    assert "12644769" in d.status.text() and window.oc_page.minima_input.rowCount() == 0


def test_bav_row_carries_the_terms_and_fetches_by_name(window):
    page = window.oc_page
    page.star.setText("AI Dra")
    asked = []
    window.run_step_for = lambda area, step, inputs, params=None, on_done=None, on_fail=None: asked.append(inputs)
    d = _dialog(window)
    assert "own use" in d.bav_note.text() and "Lichtenknecker" in d.bav_note.text()
    QTest.mouseClick(d.bav, Qt.LeftButton)
    assert asked == [{"name": "AI Dra"}]


def test_the_button_sits_beside_load_file_and_in_the_file_menu(window):
    page = window.oc_page
    assert page.databases_button.parentWidget() is page.load_button.parentWidget()
    assert any(a.text() == page.databases_button.text() for a in page.window().file_menu.actions())


def _bav_rows():
    return [record(2455000.3 + k, None, "I", "HJD unknown", "ccd", source="BAVM 244; BAV LkDB") for k in range(3)]


def _bjd_table(window):
    page = window.oc_page
    page.text.setPlainText("# times: BJD_TDB\n2455100.0 0.0001 I own\n")
    page.star.setText("AI Dra")
    window.run_step_for = lambda area, step, inputs, params=None, on_done=None, on_fail=None: on_done(
        {"minima": _bav_rows()}
    )
    return page


def test_hjd_rows_into_a_bjd_table_are_refused_without_coordinates(window):
    page = _bjd_table(window)
    d = _dialog(window)
    QTest.mouseClick(d.bav, Qt.LeftButton)
    assert page.minima_input.rowCount() == 1 and "coordinates" in d.status.text()


def test_hjd_rows_into_a_bjd_table_are_converted_with_coordinates(window):
    from astropy.coordinates import SkyCoord

    from astrowb.timeseries.minima_table import add_bjd

    page = _bjd_table(window)
    page.set_ephemeris({"name": "AI Dra", "ra": 252.0, "dec": 52.9, "period": 1.2})  # the look-up's answer
    d = _dialog(window)
    QTest.mouseClick(d.bav, Qt.LeftButton)
    expected = _bav_rows()
    add_bjd(expected, SkyCoord(252.0, 52.9, unit="deg"))
    t = page.minima_input
    got = sorted(float(t.item(r, 1).text()) for r in range(t.rowCount()))
    assert got[:3] == pytest.approx([r["bjd_tdb"] for r in expected], abs=1e-9) and got[0] != 2455000.3
    assert "Converted" in d.status.text() and "3 minima added" in d.status.text()
    errors = sorted(float(t.item(r, 2).text()) for r in range(t.rowCount()))
    assert errors[-1] == pytest.approx(expected[0]["error"]) and errors[-1] > 0.0005  # TT − UTC added

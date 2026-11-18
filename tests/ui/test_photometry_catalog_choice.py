"""PHO-25 item 3: the Stars stage's magnitude source and the overlay of its catalogue (network monkeypatched)."""

import numpy as np
import pytest
from astropy.io import fits
from astropy.table import Table

from astrowb.settings import Settings


@pytest.fixture
def window(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    yield win
    win.engine.shutdown()


def _field(window):
    page = window.photometry_page
    window.show_workspace("photometry")
    page.viewer.set_image(np.ones((100, 120), np.float32))
    h = fits.Header()
    for k, v in {"NAXIS": 2, "NAXIS1": 120, "NAXIS2": 100, "CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN",
                 "CRVAL1": 150.0, "CRVAL2": 20.0, "CRPIX1": 60.0, "CRPIX2": 50.0, "CDELT1": -0.001,
                 "CDELT2": 0.001}.items():  # fmt: skip
        h[k] = v
    page.images, page.field = ["x.fits"], {"header": h.tostring()}
    return page


def test_overlay_of_the_chosen_catalogue(window, qtbot, monkeypatch):
    page = _field(window)
    asked = []

    def run(query):
        asked.append(query)
        # one star at the centre, one far outside the frame
        return Table({"ra": [150.0, 151.0], "dec": [20.0, 20.0], "mag": [12.34, 13.0]})

    monkeypatch.setattr("astrowb.gaia._run", run)
    page.catalogue_choice.setCurrentIndex(page.catalogue_choice.findData("apass"))
    page.catalogue_button.click()
    qtbot.waitUntil(lambda: "labelled" in page.catalogue_note.text(), timeout=5000)
    assert "external.apassdr9" in asked[0]
    assert "1 star" in page.catalogue_note.text() and "labelled" in page.catalogue_note.text()
    assert "catalogue" in page.viewer.overlay_names()
    assert page.mag_source.currentData() == "apass"  # the page's source follows
    assert window.settings.get("photometry.catalogue_source") == "apass"


def test_a_failed_lookup_is_said_not_raised(window, qtbot, monkeypatch):
    page = _field(window)

    def run(query):
        raise ConnectionError("no network")

    monkeypatch.setattr("astrowb.gaia._run", run)
    page.catalogue_button.click()
    qtbot.waitUntil(lambda: "no network" in page.catalogue_note.text(), timeout=5000)
    assert "catalogue" not in page.viewer.overlay_names()


def test_without_a_solution_it_asks_for_one(window):
    page = window.photometry_page
    window.show_workspace("photometry")
    page.catalogue_button.click()
    assert page.catalogue_note.text()

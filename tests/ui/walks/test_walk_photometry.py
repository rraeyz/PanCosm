"""PHO-W accept: the practice night measured in the Photometry window in seven clicks or fewer (choose the images,
the target, Measure, Time of minimum; the comparison stars, the radii and the O−C list follow by themselves), with
each automatic choice listed in its stage."""

import pytest
from PySide6.QtWidgets import QLabel

from astrowb import sampledata

MAX_CLICKS = 7  # the practice frames carry no plate scale: the Field stage (Gaia, internet) is not part of it


@pytest.mark.slow
def test_practice_night_in_seven_clicks(walk, tmp_path):
    truth = sampledata.make(tmp_path / "night", n_lights=24)
    h = walk("en")
    h.main.open_project(tmp_path / "p.astroproj")
    h.area("photometry")
    phot = h.main.photometry_page
    h.answer(*sorted((tmp_path / "night" / "raw").glob("light_*.fits")))
    h.click("load_button")  # 1
    h.wait(lambda: phot.viewer.data is not None)
    h.click_image(phot.viewer, *truth["target_xy"])  # 2: the comparison stars and the radii follow
    h.wait(lambda: bool(phot.comps) and phot._radii_set)
    h.click("measure_button")  # 3
    h.wait(lambda: phot.light_curve is not None)
    shown = []
    phot.show_minimum = lambda m, show=phot.show_minimum: (shown.append(m), show(m))
    h.click("minimum_button")  # 4
    h.wait(lambda: bool(shown))
    h.check()
    assert len(h.timings) <= MAX_CLICKS, h.timings
    oc = h.main.oc_page.text.toPlainText()
    assert "this work" in oc  # sent to O−C by itself
    for stage in ("stars", "apertures"):  # the automatic choices and their reasons
        text = h.window.stage_panels[stage].findChild(QLabel, "automatic_choices").text()
        assert "Chosen automatically" in text and len(text) > 60

"""VAL-8: the practice night as a user goes through it: raw frames → Calibration → Photometry → time of minimum
(the guided task first-night.toml, every step clicked)."""

import pytest

from astrowb import sampledata


@pytest.mark.slow
@pytest.mark.parametrize("lang", ["en", "tr"])
def test_practice_night_from_raw_frames_to_the_time_of_minimum(walk, tmp_path, lang):
    truth = sampledata.make(tmp_path / "night", n_lights=24)
    h = walk(lang)
    h.main.open_project(tmp_path / "p.astroproj")
    h.area("calibrate")
    page = h.main.calibrate_page
    h.type("folder", str(tmp_path / "night" / "raw"))
    h.click("scan_button")
    h.wait(lambda: page.table.rowCount() > 0 and page.run_button.isEnabled())
    h.click("run_button")
    h.wait(lambda: page.photometry_button.isEnabled())
    h.click("photometry_button")
    h.area("photometry")
    phot = h.main.photometry_page
    h.wait(lambda: phot.viewer.data is not None)
    for x, y in [truth["target_xy"], *truth["comps_xy"]]:
        h.click_image(phot.viewer, x, y)
    assert phot.target is not None and phot.comps, phot.result.text()
    h.click("measure_button")
    h.wait(lambda: phot.light_curve is not None)
    shown = []
    phot.show_minimum = lambda m, show=phot.show_minimum: (shown.append(m), show(m))
    h.click("minimum_button")
    h.wait(lambda: bool(shown))
    h.check()
    assert shown[0]["time"] == pytest.approx(truth["t_min_bjd_tdb"], abs=2 / 1440)

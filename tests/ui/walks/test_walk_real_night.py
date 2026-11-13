"""Walk on a real night (VAL-8 with real data): the HAT-P-32 b transit of the EXOTIC sample (142 frames from a
6-inch telescope) used as a user would — frames opened, the target and two comparison stars clicked, the radii
chosen by the program, the light curve measured, the exact transit fitted, the night checked, everything saved.
Run with ASTROWB_VALIDATION_DATA=<folder containing HatP32Dec202017> (skipped otherwise)."""

import os
from pathlib import Path

import pytest

DATA = Path(os.environ.get("ASTROWB_VALIDATION_DATA", "/nonexistent")) / "HatP32Dec202017"
T0, P = 2455867.402743, 2.1500082  # the NASA Exoplanet Archive ephemeris EXOTIC uses for this night


@pytest.mark.skipif(not DATA.is_dir(), reason="validation data not available")
def test_hatp32_night_as_a_user(walk, tmp_path):
    frames = sorted(DATA.glob("*.FITS"))
    h = walk("en")
    h.area("photometry")
    phot = h.main.photometry_page
    h.answer(*frames)
    h.click("load_button")
    h.wait(lambda: phot.viewer.data is not None and len(phot.images) == 142)
    for x, y in ((424, 286), (465, 183), (512, 263)):  # the target, then the comparison stars, as EXOTIC's inits
        h.click_image(phot.viewer, x, y)
    assert len(phot.comps) == 2
    h.type("coord", "02:04:10.28 +46:41:16.2")
    h.click("apertures_button")
    h.wait(lambda: not h.busy())
    h.click("measure_button", budget=60.0)
    h.wait(lambda: phot.light_curve is not None)
    lc = phot.light_curve
    assert len(lc["time"]) == 142 and lc["time_scale"] == "BJD_TDB"  # clicks a few pixels off still find the stars
    h.type("period", str(P))
    h.click("transit_button")
    h.wait(lambda: phot.transit_result.text().startswith("Mid-transit"))
    fit = phot.transit_fit[1]
    tc = T0 + round((fit["values"]["tc"] - T0) / P) * P
    o_c = (fit["values"]["tc"] - tc) * 1440
    assert abs(o_c) < max(3 * fit["errors"]["tc"] * 1440, 5), o_c  # on the published ephemeris
    assert 15 < fit["derived"]["depth_ppt"] < 30  # Rp/Rs 0.149: 22 ppt
    assert phot.checks.verdict.text()  # the Checks tab judged the night
    from astrowb.ui.area_windows import _save_all

    saved = {p.name for p in _save_all(h.window, phot, str(tmp_path / "all"))}
    assert {"light_curve.lc.ecsv", "measurements.csv", "summary.pdf", "ExoClock.txt", "methods.txt"} <= saved
    h.check()

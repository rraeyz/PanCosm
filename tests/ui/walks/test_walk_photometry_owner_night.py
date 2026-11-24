"""PHO-W accept with the Field step: the owner's NY Vir night (data/owner, T100, 2018-07-10) measured in the
Photometry window — choose the images (the field is identified by itself: Gaia, VSX), make NY Vir the target from
the field's variable stars (the files' OBJECT, NSVS07826147, is another star 48° away, so the header cannot give it),
Measure, Time of minimum. The calibration is set-up, through the API as tests/validation/test_owner_cases.py does:
the Images stage takes calibrated frames and does not calibrate. Needs the internet; skipped when the field cannot be
identified for want of it, and where the owner's folder is missing."""

from pathlib import Path

import numpy as np
import pytest

OWNER = Path(__file__).resolve().parents[3] / "data" / "owner"
MAX_CLICKS = 7
NETWORK = ("internet", "offline", "reach", "connect", "timed out", "timeout", "network", "http")

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not (OWNER / "light").is_dir(), reason="the owner's night is not in data/owner"),
]


@pytest.fixture(scope="module")
def lights(tmp_path_factory):
    from astrowb import api

    out = tmp_path_factory.mktemp("owner_cal")
    frames = api.run("calibration.scan", folder=str(OWNER))["frames"]
    return sorted(api.run("calibration.run", frames=frames, output_dir=str(out))["calibrated"])


def test_owner_night_in_seven_clicks(walk, tmp_path, lights):
    h = walk("en")
    h.main.open_project(tmp_path / "p.astroproj")
    h.area("photometry")
    phot = h.main.photometry_page
    h.answer(*lights)
    h.click("load_button")  # 1: the field is identified by itself
    h.wait(lambda: phot.field is not None or "not identified" in phot.field_label.text())
    if phot.field is None:
        why = phot.field_label.text()
        if any(w in why.lower() for w in NETWORK):
            pytest.skip(f"the field was not identified for want of the network: {why}")
        pytest.fail(why)
    obj = phot.field["object"]
    assert obj["name"] == "NSVS07826147" and not obj["in_field"]  # the files name another star: said in the stage
    assert phot.target is None
    names = [v["name"] for v in phot.field["variables"]]
    assert names[0] == "NY Vir" and phot.variables.currentIndex() == 0, names  # the brightest, already chosen
    h.click("make_target")  # 2: the comparison stars and the radii follow
    h.wait(lambda: bool(phot.comps) and phot._radii_set)
    h.click("measure_button", budget=60.0)  # 3
    h.wait(lambda: phot.light_curve is not None)
    shown = []
    phot.show_minimum = lambda m, show=phot.show_minimum: (shown.append(m), show(m))
    h.click("minimum_button")  # 4
    h.wait(lambda: bool(shown))
    h.check()
    lc = phot.light_curve
    assert len(lc["time"]) == len(lights) == 20 and not lc["lost"]
    rel = np.asarray(lc["rel_flux"], float)
    mag = -2.5 * np.log10(rel / np.median(rel[:9]))  # the frames before the eclipse, as test_owner_cases
    assert 0.65 < float(mag.max()) < 0.78, np.round(mag, 3)  # its depth range
    t = np.asarray(lc["time"], float)
    deep = t[mag > mag.max() / 2]
    assert deep.min() <= shown[0]["time"] <= deep.max(), (shown[0]["time"], deep)  # timed inside the eclipse
    assert "this work" in h.main.oc_page.text.toPlainText()  # sent to O−C by itself
    assert len(h.timings) == 4 <= MAX_CLICKS, h.timings

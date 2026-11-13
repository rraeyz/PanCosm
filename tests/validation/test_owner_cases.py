"""VAL-6: the owner's own night in data/owner (NY Vir with the TÜBİTAK T100, 2018-07-10; files named NSVS07826147;
10 bias, 10 flats, 20 lights of 5-10 s, 2x2 binning). Skipped where the folder is missing.

What it pins (UF-17, UF-18 of plans/user-feedback.md): the telescope's pointing moves 90-163 px over the hour and
the calibrated frames have a bright rim (the chip's shadowed border divided by the flat); every light must become a
point (15 of 20 were left out as "not placed" because the rim pulled the frame shift to zero), the eclipse must
show, and no frame may carry a flag (an elongated comparison star's core was taken for a cosmic ray). Positions
are pixels on frame 0007 (NY Vir and four Gaia comparison stars the program chose there), so no catalogue is asked.
"""

from pathlib import Path

import numpy as np
import pytest

OWNER = Path(__file__).resolve().parents[2] / "data" / "owner"
pytestmark = pytest.mark.skipif(not (OWNER / "light").is_dir(), reason="the owner's night is not in data/owner")

TARGET = (649.0, 1292.3)  # NY Vir on NSVS07826147_0007
COMPS = [(1207.0, 777.0), (1834.7, 418.0), (1723.5, 1506.6), (1615.7, 1207.5)]


@pytest.fixture(scope="module")
def night(tmp_path_factory):
    from astrowb import api

    out = tmp_path_factory.mktemp("owner")
    frames = api.run("calibration.scan", folder=str(OWNER))["frames"]
    cal = api.run("calibration.run", frames=frames, output_dir=str(out))
    lights = sorted(cal["calibrated"])
    ref = next(p for p in lights if p.endswith("_0007_Empty.fits"))
    lc = api.run("photometry.light_curve", images=lights, target_xy=list(TARGET), comps_xy=COMPS, ref_image=ref)
    return lights, lc["light_curve"]


def test_every_frame_of_the_night_is_a_point(night, measured):
    lights, lc = night
    ok = len(lc["time"]) == len(lights) == 20 and not lc["lost"]
    measured("photometry", "frames that became points", "every light of the night", "all", len(lc["time"]), ok,
             data="owner: NY Vir, T100, 2018-07-10")  # fmt: skip
    assert ok, lc["lost"]


def test_no_flags_and_the_eclipse_shows(night, measured):
    _, lc = night
    assert all(f == "" for row in lc["flags"] for f in row), lc["flags"]
    rel = np.asarray(lc["rel_flux"], float)
    mag = -2.5 * np.log10(rel / np.median(rel[:9]))  # the frames before the eclipse
    depth = float(mag.max())
    ok = 0.65 < depth < 0.78 and float(np.std(mag[:9])) < 0.03
    measured("photometry", "primary eclipse depth (mag, white light)", "the night's own out-of-eclipse frames",
             "0.65-0.78; scatter before it < 0.03", round(depth, 3), ok, data="owner: NY Vir, T100")  # fmt: skip
    assert ok, (depth, np.round(mag, 3))

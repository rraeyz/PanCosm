"""Real-data validation: the Qatar-1 b transit night, LCO 0.4 m (elp, sq41), 2026-11-02/03, 265 calibrated frames
(e91), public. The registry set photometry/qatar1-lco holds the first 24; the whole night is fetched with the query
in data/photometry/qatar1-lco/SOURCE.md into the same folder (or $ASTROWB_DATA/photometry/qatar1-lco). Skipped
unless all 265 frames are there. Target and the four comparison stars chosen by hand: SOURCE.md; radii chosen by
the program (auto_apertures), as in the measurements quoted in plans/photometry.md.

Accepts (plans/photometry.md): PHO-33 no cloud flag on this night; PHO-34 the scaled errors make reduced χ² of the
transit fit 1.0 ± 0.1; PHO-17 item 3 the eight suggested stars give a point-to-point scatter of the target not
worse than the hand set, both measured here the same way.
"""

import os
from pathlib import Path

import numpy as np
import pytest

from astrowb import api
from astrowb.photometry.errors import point_to_point_ratio
from astrowb.photometry.quality import lc_checks

DATA = Path(os.environ.get("ASTROWB_DATA") or Path(__file__).resolve().parents[2] / "data") / "photometry/qatar1-lco"
FRAMES = sorted(DATA.glob("elp0m400-sq41-20261102-*-e91.fits.fz"))
pytestmark = [pytest.mark.validation, pytest.mark.slow,
              pytest.mark.skipif(len(FRAMES) != 265, reason="the whole Qatar-1 night (see its SOURCE.md)")]  # fmt: skip
TARGET = [1338.0, 1197.3]
COMPS = [[1255.7, 1347.1], [832.8, 1873.4], [699.9, 1761.4], [1284.8, 1441.5]]
# starts for the fit: Qatar-1 b's period and shape (the values test_ui uses), the night's mid-transit
START = {"period": 1.4200242, "tc": 2461347.6112, "k": 0.146, "a_rs": 6.25, "b": 0.645}
SET = "photometry/qatar1-lco (265 frames)"


def _measure(comps):
    return api.run("photometry.light_curve", images=FRAMES, target_xy=TARGET, comps_xy=comps,
                   auto_apertures=True)["light_curve"]  # fmt: skip


def _p2p(flux):
    """The target's point-to-point scatter: σ of successive differences / √2, of the normalised flux."""
    f = np.asarray(flux, float)
    return float(np.std(np.diff(f / np.median(f))) / np.sqrt(2))


@pytest.fixture(scope="module")
def lc():
    return _measure(COMPS)


def test_qatar1_night_has_no_cloud_flag(lc, measured):
    flags, verdict = lc_checks(lc)
    n = len(flags.get("cloud", []))
    measured("photometry", "frames flagged as cloud", "a clear night (LCO)", "0", n, n == 0, SET,
             "photometry.light_curve")  # fmt: skip
    assert len(lc["time"]) == 265 and n == 0, verdict


def test_scaled_errors_give_reduced_chi2_one(lc, measured):
    ratio, factor = point_to_point_ratio(lc["rel_flux"], lc["rel_flux_err"])
    assert factor is not None  # the Checks tab offers the scale on this night
    scaled = lc | {"rel_flux_err": (np.asarray(lc["rel_flux_err"]) * factor).tolist()}  # rel_flux_err_scaled
    chi2r = api.run("photometry.transit_fit", light_curve=scaled, **START)["transit"]["chi2r"]
    ok = abs(chi2r - 1.0) <= 0.1
    measured("photometry", f"reduced χ² of the transit fit, errors × {factor}", "1 (errors that match the scatter)",
             "± 0.1", chi2r, ok, SET, "photometry.transit_fit")  # fmt: skip
    assert ok, (ratio, chi2r)


@pytest.mark.network
# the accept is "not worse than the hand set"; its 0.44 % was measured another way (radii and definition not written),
# so both sets are measured here the same way (2026-11-28: suggested 0.45 %, hand set 0.50 %)
def test_suggested_stars_not_worse_than_the_hand_set(lc, measured):
    field = api.run("photometry.identify_field", image=FRAMES[0])["field"]
    comps = api.run("photometry.suggest_comparisons", images=FRAMES, target_xy=TARGET, field=field, n=8,
                    rules={})["comps_xy"]  # fmt: skip
    scatter, hand = _p2p(_measure(comps)["rel_flux"]), _p2p(lc["rel_flux"])
    ok = len(comps) == 8 and scatter <= hand
    measured("photometry", "point-to-point scatter of the target, the 8 suggested stars", f"the hand set ({hand:.2%})",
             "≤ the hand set", f"{scatter:.2%}", ok, SET, "photometry.suggest_comparisons")  # fmt: skip
    assert ok, (len(comps), scatter)

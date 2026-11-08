"""Real-data validation against IRAF apphot.phot (plans/photometry.md item 1): the HAT-P-32 sample night (EXOTIC,
see test_hatp32b.py) measured by IRAF 2.17 phot with our centres, the same radii (4, 10, 16 px) and the same sky
algorithm (median after 3-sigma rejection, 10 times), gain 1, no read noise. The reduced IRAF table
(data/hatp32_iraf_phot.csv: flux, sky, its scatter and pixel count, aperture area and IRAF's flux error for the
target and two comparison stars on all 142 frames) was made with the scratchpad script p1/hatp.py.

Agreement: the fluxes differ by +0.015 % (IRAF weights the aperture's edge pixels linearly, we by the exact area).
These frames are raw integer ADU: IRAF's median of the sky ring is sometimes a whole number and sometimes interpolated,
ours is interpolated inside its unit bin (aperture._grouped_median), so a faint comparison star on a few frames
differs by up to 0.6 %. Run with ASTROWB_VALIDATION_DATA=<folder containing HatP32Dec202017>.
"""

import os
import warnings
from pathlib import Path

import numpy as np
import pytest

from astrowb.photometry.lightcurve import light_curve

DATA = Path(os.environ.get("ASTROWB_VALIDATION_DATA", "/nonexistent")) / "HatP32Dec202017"
REF = Path(__file__).parent / "data" / "hatp32_iraf_phot.csv"
pytestmark = pytest.mark.skipif(not DATA.is_dir(), reason="validation data not available")


@pytest.fixture(scope="module")
def both():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        lc = light_curve(sorted(DATA.glob("*.FITS")), (424, 286), [(465, 183), (512, 263)], 4.0, 10.0, 16.0)
    ref = np.genfromtxt(REF, delimiter=",", names=True, dtype=None, encoding=None)
    n = len(lc["file"])
    assert n == 142 and len(ref) == 3 * n
    return lc, {k: ref[k].reshape(n, 3) for k in ("x", "y", "flux", "flux_err")}


def test_same_centres(both):
    lc, ref = both
    xy = np.asarray(lc["xy"])
    assert np.max(np.abs(xy[..., 0] - ref["x"])) < 0.01 and np.max(np.abs(xy[..., 1] - ref["y"])) < 0.01


def test_fluxes_and_relative_flux_agree_with_iraf(both):
    lc, ref = both
    ours = np.column_stack([lc["target_flux"], lc["comp_flux"]])
    ratio = ref["flux"] / ours
    assert np.all(np.abs(np.median(ratio, axis=0) - 1) < 0.001)  # the plan's limit: 0.1 % per frame (median)
    assert np.max(np.abs(ratio - 1)) < 0.008  # integer sky medians (see above)
    rel_iraf = ref["flux"][:, 0] / ref["flux"][:, 1:].sum(axis=1)
    d = rel_iraf / np.asarray(lc["rel_flux"]) - 1
    assert np.median(np.abs(d)) < 0.001 and np.max(np.abs(d)) < 0.008


def test_flux_errors_agree_with_iraf(both):
    lc, ref = both
    ours = np.column_stack([lc["target_flux_err"], lc["comp_flux_err"]])
    assert np.all(np.abs(np.median(ref["flux_err"] / ours, axis=0) - 1) < 0.1)  # the plan's limit: 10 %

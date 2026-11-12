"""Real-data validation: HAT-P-32 b transit, 142 frames from a 6-inch MicroObservatory telescope
(EXOTIC sample data, github.com/rzellem/EXOTIC_sampledata, 2017-12-20, uncalibrated, no darks/flats).

Reference: ephemeris and radius ratio used by EXOTIC for this data set (inits.json, NASA Exoplanet
Archive values): T0 = 2455867.402743 BJD, P = 2.1500082 d (+-1.3e-7, so the prediction for this
epoch is good to ~12 s), Rp/Rs = 0.1489 (depth ~2.2 %), T14 ~ 3.1 h.

Run with ASTROWB_VALIDATION_DATA=<folder containing HatP32Dec202017>.
"""

import os
import warnings
from pathlib import Path

import numpy as np
import pytest

from astrowb.photometry.lightcurve import light_curve, normalise
from astrowb.timeseries.minima import kwee_van_woerden, trapezoid_fit

DATA = Path(os.environ.get("ASTROWB_VALIDATION_DATA", "/nonexistent")) / "HatP32Dec202017"
pytestmark = pytest.mark.skipif(not DATA.is_dir(), reason="validation data not available")
T0, P = 2455867.402743, 2.1500082


@pytest.fixture(scope="module")
def lc():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        # pixel positions of target and comparisons as given in EXOTIC's inits.json
        out = light_curve(
            sorted(DATA.glob("*.FITS")),
            (424, 286),
            [(465, 183), (512, 263)],
            4.0,
            10.0,
            16.0,
            coord="02:04:10.28 +46:41:16.2",
        )
    t = np.array(out["time"])
    tc = T0 + round((t.mean() - T0) / P) * P
    oot = np.abs(t - tc) > 0.075
    f = normalise(out["rel_flux"], oot)
    err = np.array(out["rel_flux_err"]) / np.median(np.array(out["rel_flux"])[oot])
    return t, f, err, tc, oot


def test_photometry_quality(lc):
    t, f, _, _, oot = lc
    assert len(t) == 142
    assert np.std(f[oot]) < 0.012  # 6-inch telescope, V = 11.4, 60 s
    assert np.all(np.abs(f - 1) < 0.06)  # no lost stars or bad frames


def test_transit_time_depth_duration(lc, measured):
    t, f, err, tc, _ = lc
    fit = trapezoid_fit(t, f, err)
    oc_min = (fit["t0"] - tc) * 1440
    ok = abs(oc_min) < 3 * fit["t0_err"] * 1440 and abs(oc_min) < 15
    measured("Photometry", "transit mid-time", "the published ephemeris", "3σ and 15 min", f"{oc_min:+.1f} min", ok,
             "HAT-P-32 b (EXOTIC sample)", "PHO-26")  # fmt: skip
    assert abs(oc_min) < 3 * fit["t0_err"] * 1440 and abs(oc_min) < 15, oc_min
    assert 0.016 < fit["depth"] < 0.028
    assert 2.5 < fit["t14"] * 24 < 3.6


def test_kvw_agrees(lc):
    t, f, _, tc, _ = lc
    tm, s_kvw, s_boot = kwee_van_woerden(t, f)
    assert abs(tm - tc) < 3 * max(s_kvw, s_boot) and abs(tm - tc) * 1440 < 15

"""VAL-5 accept: a deliberate change of the sky estimator moves the photometry rows, and the science changelog
(tools/validation_report.diff) lists them. The HAT-P-32 sample night as in test_iraf_phot (skipped without it)."""

import importlib.util
import os
import warnings
from pathlib import Path

import numpy as np
import pytest

from astrowb.photometry.lightcurve import light_curve

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("ASTROWB_VALIDATION_DATA", "/nonexistent")) / "HatP32Dec202017"
REF = Path(__file__).parent / "data" / "hatp32_iraf_phot.csv"
pytestmark = pytest.mark.skipif(not DATA.is_dir(), reason="validation data not available")
spec = importlib.util.spec_from_file_location("validation_report", ROOT / "tools" / "validation_report.py")
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


def _row(sky_method):
    """The aperture-flux row of test_iraf_phot, measured with the given sky estimator."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        lc = light_curve(sorted(DATA.glob("*.FITS")), (424, 286), [(465, 183), (512, 263)], 4.0, 10.0, 16.0,
                         sky_method=sky_method)  # fmt: skip
    ref = np.genfromtxt(REF, delimiter=",", names=True, dtype=None, encoding=None)["flux"].reshape(-1, 3)
    ratio = ref / np.column_stack([lc["target_flux"], lc["comp_flux"]])
    worst = float(np.max(np.abs(np.median(ratio, axis=0) - 1)))
    return {"area": "Photometry", "quantity": "aperture flux (median per star)", "tolerance": "0.1 %",
            "measured": f"{100 * worst:.3f} %"}  # fmt: skip


def test_a_changed_sky_estimator_appears_in_the_science_changes():
    before, after = [_row("median")], [_row("mode")]  # IRAF's median against its mode (3 median - 2 mean)
    moved = report.diff(before, after)
    assert [m[1] for m in moved] == ["aperture flux (median per star)"], (before, after)
    assert report.diff(before, [_row("median")]) == []  # the same estimator again: nothing listed

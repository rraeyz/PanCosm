"""PHO-19 accept: the Qatar-1 night replayed file by file into a followed folder gives the night run's numbers.
The first 24 frames of the registry set photometry/qatar1-lco (tools/fetch_data.py); skipped without them."""

import os
import shutil
from pathlib import Path

import numpy as np
import pytest

from astrowb.photometry import live
from astrowb.photometry.lightcurve import light_curve

DATA = Path(os.environ.get("ASTROWB_DATA") or Path(__file__).resolve().parents[2] / "data") / "photometry/qatar1-lco"
FRAMES = sorted(DATA.glob("elp0m400-sq41-20261102-*-e91.fits.fz"))[:24]
pytestmark = [pytest.mark.validation, pytest.mark.slow,
              pytest.mark.skipif(len(FRAMES) < 24, reason="the Qatar-1 set (tools/fetch_data.py)")]  # fmt: skip
TARGET = [1338.0, 1197.3]
COMPS = [[1255.7, 1347.1], [832.8, 1873.4], [699.9, 1761.4], [1284.8, 1441.5]]
RADII = (9.5, 18.75, 26.69)  # the radii the program chose for this night (test_qatar1_night)


def test_the_night_replayed_live_equals_the_night_run(tmp_path, measured):
    folder, seen = tmp_path / "night", set()
    folder.mkdir()
    session = live.LiveLightCurve(TARGET, COMPS, *RADII)
    for i, p in enumerate(FRAMES):  # one file arrives, the folder is polled, as during the night
        shutil.copy(p, folder / p.name)
        os.utime(folder / p.name, (1000 + i, 1000 + i))
        for new in live.ready_files(folder, seen, now=5000 + i):
            seen.add(new)
            assert session.add(new) is not None, session.failed
    got = session.light_curve()
    want = light_curve(sorted(str(p) for p in folder.iterdir()), TARGET, COMPS, *RADII)
    assert got["time"] == want["time"]
    # the same numbers up to the last bits: the night run reads only the part of a frame around the stars
    worst = max(float(np.max(np.abs(np.subtract(got[k], want[k])))) for k in ("rel_flux", "rel_flux_err"))
    ok = worst < 1e-12
    measured("photometry", "live against the night run, largest difference in rel_flux and its error",
             "the night run", "< 1e-12", f"{worst:.1e}", ok, "photometry/qatar1-lco (24 frames)",
             "photometry.light_curve")  # fmt: skip
    assert ok, worst

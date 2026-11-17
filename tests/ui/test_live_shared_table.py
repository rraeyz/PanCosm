"""PHO-19: the live light curve feeds the same result views as a night run, one frame at a time."""

import os
import sys
from pathlib import Path

import numpy as np
from astropy.io import fits

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_live import STARS, write_frames  # noqa: E402

from astrowb.photometry import live  # noqa: E402
from astrowb.ui.photometry_live import Throttled  # noqa: E402
from astrowb.ui.photometry_page import PhotometryPage  # noqa: E402


def _plotted(page):
    seen = []
    real = page.plot.set_figure
    page.plot.set_figure = lambda fig, keep=False: (seen.append(len(fig.panels[0].series[0].x)), real(fig, keep))[1]
    return seen


def test_live_rows_grow_with_each_frame_and_lost_frame_has_its_reason(qtbot, tmp_path):
    paths = write_frames(tmp_path, 5)
    blank = tmp_path / "f99.fits"  # clouds: no star at all
    h = fits.Header({"DATE-OBS": "2026-10-01T21:00:00", "EXPTIME": 30.0, "GAIN": 2.0, "IMAGETYP": "Light"})
    fits.PrimaryHDU(np.random.default_rng(1).normal(100, 3, (60, 80)).astype(np.float32), h).writeto(blank)
    os.utime(blank, (2000, 2000))
    page = PhotometryPage()
    qtbot.addWidget(page)
    page.target, page.comps = STARS[0][:2], [s[:2] for s in STARS[1:]]
    page.live = live.LiveLightCurve(page.target, page.comps, 4, 10, 16, "02:04:10 +46:41:16")
    plotted = _plotted(page)
    for n, p in enumerate(paths, 1):
        page.live.add(p)
        page._live_show()
        assert page.meas_table.rowCount() == n and page.frame_table.rowCount() == n
        assert plotted[-1] == n
    page.live.add(str(blank))  # arrives like any frame
    page._live_show()
    assert page.frame_table.rowCount() == 6 and page.meas_table.rowCount() == 5
    item = page.frame_table.item(5, 0)
    assert item.toolTip() and item.text() == "f99.fits"


def test_throttle_runs_at_most_once_per_interval(qtbot):
    calls = []
    t = Throttled(None, lambda: calls.append(1), ms=50)
    for _ in range(20):
        t.request()
    assert len(calls) == 1  # the first at once, the rest wait
    qtbot.waitUntil(lambda: len(calls) == 2, timeout=2000)
    qtbot.wait(120)
    assert len(calls) == 2


def test_live_refresh_keeps_choices_and_exception_reason(qtbot, tmp_path):
    paths = write_frames(tmp_path, 4)
    bad = tmp_path / "f98.fits"
    bad.write_bytes(b"not a fits file")
    page = PhotometryPage()
    qtbot.addWidget(page)
    page.target, page.comps = STARS[0][:2], [s[:2] for s in STARS[1:]]
    page.live = live.LiveLightCurve(page.target, page.comps, 4, 10, 16, "02:04:10 +46:41:16")
    for p in paths[:3]:
        page.live.add(p)
    page._live_show()
    page.excluded, page.comp_off = {1}, {0}  # the user left out frame 1 and comparison C1
    page.live.add(paths[3])
    page.live.add(str(bad))
    page._live_show()
    assert page.excluded == {1} and page.comp_off == {0}
    assert page.frame_table.rowCount() == 5
    assert len(page.light_curve["rel_flux"]) == 3  # four measured, one excluded
    why = page.frame_table.item(4, 0).toolTip()
    assert why and "stars were not found" not in why

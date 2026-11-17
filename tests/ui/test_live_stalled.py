"""PHO-19: a stalled night (no frame for 3 x the cadence) shows a banner, not an error; a new frame removes it."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from PySide6.QtCore import QTimer
from test_live import STARS, write_frames  # noqa: E402

from astrowb.photometry import live  # noqa: E402
from astrowb.ui.photometry_live import StallWatch  # noqa: E402
from astrowb.ui.photometry_page import PhotometryPage  # noqa: E402


def _setup(qtbot, tmp_path, n):
    paths = write_frames(tmp_path, n)  # one frame a minute
    page = PhotometryPage()
    qtbot.addWidget(page)
    session = live.LiveLightCurve(STARS[0][:2], [s[:2] for s in STARS[1:]], 4, 10, 16, "02:04:10 +46:41:16")
    now = [0.0]
    watch = StallWatch(page.layout(), session, QTimer(page), clock=lambda: now[0])
    return paths, session, watch, now


def test_banner_after_three_cadences_and_new_frame_hides_it(qtbot, tmp_path):
    paths, session, watch, now = _setup(qtbot, tmp_path, 5)
    for p in paths[:4]:
        session.add(p)
    watch.check()
    now[0] = 179
    watch.check()
    assert watch.banner is None
    now[0] = 180
    watch.check()
    assert watch.banner is not None and "3 min" in watch.banner.text() and "60 s" in watch.banner.text()
    session.add(paths[4])
    now[0] = 181
    watch.check()
    assert watch.banner is None


def test_fewer_than_three_frames_no_banner(qtbot, tmp_path):
    paths, session, watch, now = _setup(qtbot, tmp_path, 2)
    for p in paths:
        session.add(p)
    watch.check()
    now[0] = 10000
    watch.check()
    assert watch.banner is None

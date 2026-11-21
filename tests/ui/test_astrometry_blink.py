"""UI-16.11: the Astrometry window blinks its frames (time order) in the blink window."""

import numpy as np
from astropy.io import fits

from astrowb.settings import Settings
from astrowb.ui.moving_dialog import MovingObjectPage


def frames(tmp_path, times, tag="a"):
    out = []
    for i, t in enumerate(times):
        p = tmp_path / f"{tag}{i}.fits"
        fits.PrimaryHDU(np.full((16, 16), 100.0, np.float32), fits.Header({"DATE-OBS": t, "EXPTIME": 30.0})).writeto(p)
        out.append(str(p))
    return out


def test_blink_needs_two_frames_and_follows_time_order(qtbot, tmp_path):
    page = MovingObjectPage(Settings(tmp_path))
    qtbot.addWidget(page)
    assert not page.blink_button.isEnabled()
    page.set_images(frames(tmp_path, ["2026-11-15T21:00:00"]))
    assert not page.blink_button.isEnabled()
    three = frames(tmp_path, ["2026-11-15T23:00:00", "2026-11-15T21:00:00", "2026-11-15T22:00:00"], "b")
    page.set_images(three)
    assert page.blink_button.isEnabled()
    page.blink_button.click()
    qtbot.addWidget(page.blink)
    assert page.blink.paths == [three[1], three[2], three[0]] and page.blink.align.isChecked()

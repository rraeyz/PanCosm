"""PHO-24: the Astrometry window measures a pair of stars on its frame and adds it to the same Pairs table."""

import sys
from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits

from astrowb.settings import Settings
from astrowb.ui.moving_dialog import MovingObjectPage

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_pair_measure import pair_image  # noqa: E402


def test_a_line_between_stars_adds_the_pair(qtbot, tmp_path):
    img, w, (x1, y1), (x2, y2), sep = pair_image()
    paths = []
    for i, t in enumerate(("2026-11-15T21:00:00", "2026-11-15T23:00:00")):
        h = w.to_header()
        h["DATE-OBS"] = t
        paths.append(str(tmp_path / f"f{i}.fits"))
        fits.PrimaryHDU(img.astype(np.float32), h).writeto(paths[-1])
    page = MovingObjectPage(Settings(tmp_path))
    qtbot.addWidget(page)
    assert not page.pair_button.isEnabled()
    page.set_images(paths)
    page.pair_button.setChecked(True)
    assert page.viewer.tool == "line"
    page.viewer.line_selected.emit(x1 + 30, y1, x2, y2)  # one end on blank sky: no pair
    assert page.pair_table.last is None and not page.pair_table.add_button.isEnabled()
    page.viewer.line_selected.emit(x1 + 1, y1, x2, y2 - 1)
    page.pair_table.add_button.click()
    t = page.pair_table.table.model.table
    assert len(t) == 1 and t["separation_px"][0] == pytest.approx(sep, abs=0.05)
    assert t["position_angle"][0] == pytest.approx(123.0, abs=0.2)  # the frame's own WCS
    page.pair_button.setChecked(False)
    assert page.viewer.tool == "pan" and page.first is None

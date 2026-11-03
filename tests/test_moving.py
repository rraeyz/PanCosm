"""Moving-object astrometry: a simulated asteroid crossing solved frames; the ADES report."""

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS

from astrowb.engine.steps import execute
from astrowb.photometry.moving import ades_psv

HEADER = {
    "CTYPE1": "RA---TAN",
    "CTYPE2": "DEC--TAN",
    "CRVAL1": 150.0,
    "CRVAL2": 20.0,
    "CRPIX1": 60.5,
    "CRPIX2": 50.5,
    "CD1_1": -0.0003,
    "CD1_2": 0.0,
    "CD2_1": 0.0,
    "CD2_2": 0.0003,
}


class Ctx:
    def progress(self, *a):
        pass


def make_frames(tmp_path, n=6):
    yy, xx = np.mgrid[:100, :120]
    paths, truth = [], []
    for i in range(n):
        x, y = 20.0 + 14.3 * i, 30.0 + 6.1 * i  # moving 14.3, 6.1 px per frame
        img = 100 + 4000 * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / 4.0)
        img += 3000 * np.exp(-((xx - 90.0) ** 2 + (yy - 20.0) ** 2) / 4.0)  # a fixed star
        h = fits.Header(HEADER | {"DATE-OBS": f"2026-11-15T21:{10 + 2 * i:02d}:00", "EXPTIME": 60.0})
        fits.PrimaryHDU((img + np.random.default_rng(i).normal(0, 3, img.shape)).astype(np.float32), h).writeto(
            tmp_path / f"a{i}.fits"
        )
        paths.append(str(tmp_path / f"a{i}.fits"))
        truth.append(WCS(h).pixel_to_world(x, y))
    return paths, truth


def test_track_measures_the_moving_object(tmp_path):
    paths, truth = make_frames(tmp_path)
    inputs = {"images": paths, "first_xy": [21.0, 29.0], "last_xy": [91.0, 61.0]}  # rough clicks
    rows = execute("astrometry.moving", inputs, {}, Ctx())["positions"]
    assert len(rows) == 6 and rows[0]["time"].startswith("2026-11-15T21:10:30")  # mid-exposure
    for r, sky in zip(rows, truth, strict=True):
        assert np.hypot((r["ra"] - sky.ra.deg) * np.cos(np.radians(20)), r["dec"] - sky.dec.deg) * 3600 < 0.2
        assert r["resid"] < 0.3


def test_ades_report():
    rows = [{"time": "2026-11-15T21:10:30.000", "ra": 150.012345, "dec": 20.0012}]
    text = ades_psv(rows, "2026 VA12", "A84", ["A. Gözlemci"], telescope={"aperture": 0.6})
    assert text.startswith("# version=2017\n# observatory\n! mpcCode A84")
    assert "|2026 VA12||CCD|A84|2026-11-15T21:10:30.000Z|150.012345|+20.001200|Gaia3" in text
    assert "|||CCD" not in text and "! aperture 0.6" in text
    assert ades_psv(rows, "433", "A84", ["X"]).splitlines()[-1].startswith("433||")
    assert ades_psv(rows, "MyObj1", "A84", ["X"]).splitlines()[-1].startswith("||MyObj1|")
    with pytest.raises(ValueError, match="observatory code"):
        ades_psv(rows, "2026 VA12", "", ["X"])


def test_dialog_marks_measures_and_writes_the_report(qtbot, tmp_path):
    from astrowb.settings import Settings
    from astrowb.ui.main_window import MainWindow

    paths, _ = make_frames(tmp_path)
    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    try:
        dlg = win.moving_dialog()
        dlg.set_images(list(reversed(paths)))  # any order: sorted by time
        dlg._clicked(21.0, 29.0)
        dlg._clicked(91.0, 61.0)
        assert dlg.measure_button.isEnabled()
        dlg.measure_button.click()
        qtbot.waitUntil(lambda: dlg.table.rowCount() == 6, timeout=60000)
        dlg.designation.setText("2026 VA12")
        assert dlg.export(str(tmp_path / "r.psv")) is None and "required" in dlg.hint.text()  # no code yet
        dlg.code.setText("a84")
        dlg.observers.setText("A. Gözlemci, B. Yardımcı")
        dlg.export(str(tmp_path / "r.psv"))
        text = (tmp_path / "r.psv").read_text(encoding="utf-8")
        assert text.count("|2026 VA12||CCD|A84|") == 6 and "! name B. Yardımcı" in text
        assert win.settings.get("mpc")["code"] == "A84"  # remembered for the next object
    finally:
        win.engine.shutdown()

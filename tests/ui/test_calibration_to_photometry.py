"""CAL-22 / PHO-19: Calibrate's "Send each calibrated frame to Photometry" feeds Photometry's live mode."""

import shutil
import sys
from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits
from PySide6.QtWidgets import QFileDialog

from astrowb.engine.steps import execute
from astrowb.photometry.lightcurve import light_curve
from astrowb.settings import Settings

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_live import STARS, write_frames  # noqa: E402


class Ctx:
    def progress(self, *a):
        pass

    def check(self):
        pass


@pytest.fixture
def night(tmp_path):
    rng = np.random.default_rng(5)
    raw, lights, inbox = tmp_path / "raw", tmp_path / "lights", tmp_path / "inbox"
    for d in (raw, lights, inbox):
        d.mkdir()
    for i in range(3):
        for name, level, extra in (("b", 20, {"IMAGETYP": "BIAS"}), ("d", 30, {"IMAGETYP": "DARK", "EXPTIME": 30.0}),
                                   ("f", 20300, {"IMAGETYP": "FLAT", "EXPTIME": 1.0})):  # fmt: skip
            fits.PrimaryHDU((level + rng.normal(0, 3, (60, 80))).astype(np.float32),
                            fits.Header(extra)).writeto(raw / f"{name}{i}.fits")  # fmt: skip
    paths = write_frames(lights, 6)
    scan = execute("calibration.scan", {"folder": str(raw), "lights": str(lights)}, {}, Ctx())
    return scan["frames"], paths, inbox


def _page(window, tmp_path, frames, monkeypatch, inbox):
    page = window.calibrate_page
    page.output.setText(str(tmp_path / "live"))
    page.show_result(execute("calibration.run", {"frames": frames, "output_dir": str(tmp_path / "b")}, {}, Ctx()))
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a, **k: str(inbox))
    page.follow_send.setChecked(True)
    page.follow_button.setChecked(True)
    return page


@pytest.fixture
def window(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    yield win
    win.engine.shutdown()


def test_calibrated_frames_reach_live_photometry_and_equal_the_batch(window, qtbot, tmp_path, monkeypatch, night):
    frames, paths, inbox = night
    page = _page(window, tmp_path, frames, monkeypatch, inbox)
    phot = window.photometry_page
    phot.set_images(paths[:1])
    for sx, sy, _ in STARS:
        phot._clicked(sx, sy)
    folder = tmp_path / "phot_folder"
    folder.mkdir()
    assert phot.start_live(str(folder)) is True
    for p in paths:
        shutil.copy(p, inbox / Path(p).name)
        page.follower.scan()
    qtbot.waitUntil(lambda: len(phot.live.points) == 6, timeout=60000)
    phot.stop_live()
    calibrated = sorted(str(p) for p in (tmp_path / "live").glob("*.fits"))
    radii = (phot.r_ap.value(), phot.r_in.value(), phot.r_out.value())
    batch = light_curve(calibrated, STARS[0][:2], [s[:2] for s in STARS[1:]], *radii)
    ours = phot.live.light_curve()["rel_flux"]
    assert np.allclose(ours, batch["rel_flux"], rtol=1e-9, atol=0)


def test_not_started_says_so_and_queues(window, tmp_path, monkeypatch, night):
    frames, paths, inbox = night
    page = _page(window, tmp_path, frames, monkeypatch, inbox)
    shutil.copy(paths[0], inbox / "f00.fits")
    page.follower.scan()
    assert "Photometry is not measuring yet" in page.result.text() and page.follow_button.isChecked()
    assert len(window.photometry_page.live_fed) == 1

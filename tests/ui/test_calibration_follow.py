"""CAL-22: "Follow a folder" in the Calibrate stage: a replayed night equals the batch run, errors do not stop it."""

import shutil
from pathlib import Path

import numpy as np
from astropy.io import fits
from PySide6.QtWidgets import QFileDialog

from astrowb.engine.steps import execute
from astrowb.ui.calibrate_page import CalibratePage


class Ctx:
    def progress(self, *a):
        pass

    def check(self):
        pass


def _night(tmp_path):
    rng = np.random.default_rng(3)
    raw, lights = tmp_path / "raw", tmp_path / "lights"
    raw.mkdir()
    lights.mkdir()
    shape = (40, 50)
    for i in range(4):
        for name, level, extra in (("b", 300, {"IMAGETYP": "BIAS"}), ("d", 310, {"IMAGETYP": "DARK", "EXPTIME": 30.0}),
                                   ("f", 20300, {"IMAGETYP": "FLAT", "EXPTIME": 1.0})):  # fmt: skip
            fits.PrimaryHDU((level + rng.normal(0, 3, shape)).astype(np.float32),
                            fits.Header(extra)).writeto(raw / f"{name}{i}.fits")  # fmt: skip
        fits.PrimaryHDU((900 + rng.normal(0, 10, shape)).astype(np.float32),
                        fits.Header({"IMAGETYP": "LIGHT", "EXPTIME": 30.0,
                                     "DATE-OBS": f"2026-11-14T20:0{i}:00"})).writeto(lights / f"l{i}.fits")  # fmt: skip
    scan = execute("calibration.scan", {"folder": str(raw), "lights": str(lights)}, {}, Ctx())
    return scan["frames"], lights


def _start(page, monkeypatch, folder):
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a, **k: str(folder))
    page.follow_button.setChecked(True)


def test_follow_refuses_without_masters(qtbot):
    page = CalibratePage()
    qtbot.addWidget(page)
    page.follow_button.setChecked(True)
    assert not page.follow_button.isChecked() and "masters first" in page.result.text()


def test_replayed_night_equals_the_batch_and_errors_do_not_stop(qtbot, tmp_path, monkeypatch):
    frames, lights = _night(tmp_path)
    batch = execute("calibration.run", {"frames": frames, "output_dir": str(tmp_path / "batch")}, {}, Ctx())
    page = CalibratePage()
    qtbot.addWidget(page)
    page.output.setText(str(tmp_path / "live"))
    page.show_result(batch)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    _start(page, monkeypatch, inbox)
    (inbox / "bad.fits").write_bytes(b"not a fits file")
    page.follower.scan()
    assert "bad.fits" in page.result.text() and page.follow_button.isChecked()
    for p in sorted(lights.glob("*.fits")):
        shutil.copy(p, inbox / p.name)
        page.follower.scan()
    assert "4 frames calibrated, last l3.fits" in page.result.text()
    for p in batch["calibrated"]:
        ours = tmp_path / "live" / Path(p).name
        assert np.array_equal(fits.getdata(ours, "SCI"), fits.getdata(p, "SCI"))
    page.follow_button.setChecked(False)
    assert not page.follower.poll.isActive()

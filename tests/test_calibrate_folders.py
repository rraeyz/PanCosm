"""Lights and calibration frames in different folders (as observers keep them), and a clear word when there is
nothing to calibrate."""

import numpy as np
from astropy.io import fits

from astrowb.engine.steps import execute


class Ctx:
    def progress(self, *a):
        pass

    def check(self):
        pass


def write(folder, name, kind, exptime=10.0, temp=-95.54999999999998):
    folder.mkdir(parents=True, exist_ok=True)
    h = fits.Header({"IMAGETYP": kind, "EXPTIME": exptime, "CCD-TEMP": temp})
    fits.PrimaryHDU(np.full((8, 8), 100, np.float32), h).writeto(folder / name)


def test_scan_reads_several_folders_once_each(tmp_path):
    night, library = tmp_path / "night", tmp_path / "library"
    write(night / "Light", "l1.fits", "Light Frame")
    write(night / "BDF", "b1.fits", "Bias Frame", 0.0)
    write(library, "d1.fits", "Dark Frame")
    out = execute("calibration.scan", {"folder": f"{night}; {library} ; {night / 'BDF'}"}, {}, Ctx())
    kinds = sorted(f["kind"] for f in out["frames"])
    assert kinds == ["bias", "dark", "light"]  # the BDF folder given twice is read once


def test_page_says_why_calibrate_is_off_and_adds_folders(qtbot, tmp_path):
    from astrowb.ui.workspaces import CalibratePage

    write(tmp_path / "BDF", "b1.fits", "Bias Frame", 0.0)
    frames = execute("calibration.scan", {"folder": str(tmp_path / "BDF")}, {}, Ctx())["frames"]
    page = CalibratePage()
    qtbot.addWidget(page)
    page.folder.setText(str(tmp_path / "BDF"))
    page.show_frames(frames, [])
    assert not page.run_button.isEnabled() and "No light frames" in page.warnings.toPlainText()
    assert page.table.item(0, 4).text() == "-95.5"  # not -95.54999999999998
    with qtbot.waitSignal(page.scan_requested):  # a folder added is read at once, no Scan press
        page._add_folder(str(tmp_path / "Light"))
    assert page.folder.text() == f"{tmp_path / 'BDF'}; {tmp_path / 'Light'}"
    assert page.output.text() == str(tmp_path / "BDF" / "calibrated")


def test_a_bad_flat_group_does_not_stop_the_night(tmp_path):
    """Flats that are not flats (darker than the bias) cannot make a master: the lights are calibrated without
    it and the failure is reported, instead of the whole calibration failing."""
    night = tmp_path / "night"
    for i in range(3):
        write(night / "BDF", f"b{i}.fits", "Bias Frame", 0.0)
        write(night / "Light", f"l{i}.fits", "Light Frame")
    for i in range(3):  # "flats" at 50 ADU, below the 100 ADU bias
        night.joinpath("BDF").mkdir(exist_ok=True)
        h = fits.Header({"IMAGETYP": "Flat Field", "EXPTIME": 1.0, "CCD-TEMP": -10.0})
        fits.PrimaryHDU(np.full((8, 8), 50, np.float32), h).writeto(night / "BDF" / f"f{i}.fits")
    frames = execute("calibration.scan", {"folder": str(night)}, {}, Ctx())["frames"]
    out = execute("calibration.run", {"frames": frames, "output_dir": str(tmp_path / "cal")}, {}, Ctx())
    assert len(out["calibrated"]) == 3 and [f["kind"] for f in out["failed_masters"]] == ["flat"]
    assert fits.getheader(out["calibrated"][0])["CALF"] == "none"


def test_frames_are_removed_and_the_list_cleared_with_undo(qtbot, tmp_path):
    """The owner: a master from an earlier run got into the list and could not be taken out, and there was no way
    to empty the list and choose the folders again. Delete / "Remove from the list", "Clear", Ctrl+Z."""
    from PySide6.QtCore import Qt

    from astrowb.ui.workspaces import CalibratePage

    for name, kind, t in (("b1.fits", "Bias Frame", 0.0), ("master_bias_00.fits", "Master bias", 0.0)):
        write(tmp_path / "BDF", name, kind, t)
    write(tmp_path / "Light", "l1.fits", "Light Frame")  # 10 s, no dark: the message rounds the temperature
    frames = execute("calibration.scan", {"folder": str(tmp_path)}, {}, Ctx())["frames"]
    page = CalibratePage()
    qtbot.addWidget(page)
    page.folder.setText(str(tmp_path))
    page.show_frames(frames, [])
    assert "-95.5 °C" in page.warnings.toPlainText() and "-95.54999" not in page.warnings.toPlainText()
    master = next(r for r, f in enumerate(page.frames) if "master" in f["path"])
    page.table.selectRow(master)
    qtbot.keyClick(page.table, Qt.Key_Delete)
    assert len(page.frames) == 2 and not any("master" in f["path"] for f in page.frames)
    page.undo_stack.undo()
    assert len(page.frames) == 3 and page.table.rowCount() == 3
    page._clear()
    assert page.frames == [] and page.folder.text() == "" and page.table.rowCount() == 0
    assert not page.run_button.isEnabled()
    page.undo_stack.undo()
    assert len(page.frames) == 3 and page.folder.text() == str(tmp_path)
    page.show_frames(frames, [])  # a new scan: nothing of the old list to undo
    assert page.undo_stack.count() == 0

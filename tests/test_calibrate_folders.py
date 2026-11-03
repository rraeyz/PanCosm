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

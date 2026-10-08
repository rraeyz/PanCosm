"""Files as they come from the many capture programs: colour cubes, one-plane cubes, 8-bit / 64-bit / integer
data, compressed .fz, no time or exposure in the header. Calibration, stacking and photometry take them all."""

import numpy as np
import pytest
from astropy.io import fits

from astrowb.engine.steps import execute

YY, XX = np.mgrid[:64, :80]


class Ctx:
    def progress(self, *a):
        pass

    def check(self):
        pass


def frame(i, rng):
    stars = 20000 * np.exp(-((XX - 30 - i % 2) ** 2 + (YY - 20) ** 2) / 4)
    stars += 15000 * np.exp(-((XX - 60) ** 2 + (YY - 45) ** 2) / 4)
    return 500 + stars + rng.normal(0, 5, (64, 80))


LAYOUTS = {
    "colour cube": lambda d: np.stack([d] * 3).astype(np.float32),
    "one-plane cube": lambda d: d[None].astype(np.float32),
    "8-bit": lambda d: np.clip(d / 100, 0, 255).astype(np.uint8),
    "64-bit float": lambda d: d.astype(np.float64),
    "32-bit integer": lambda d: d.astype(np.int32),
}


@pytest.mark.parametrize("layout", list(LAYOUTS))
def test_layouts_calibrate_stack_and_measure(tmp_path, layout):
    rng = np.random.default_rng(1)
    night = tmp_path / "night" / "lights"
    night.mkdir(parents=True)
    for i in range(3):
        h = fits.Header({"IMAGETYP": "Light Frame", "EXPTIME": 10.0, "DATE-OBS": f"2025-01-01T20:0{i}:00"})
        fits.PrimaryHDU(LAYOUTS[layout](frame(i, rng)), h).writeto(night / f"l{i}.fits")
    scan = execute("calibration.scan", {"folder": str(tmp_path / "night")}, {}, Ctx())
    assert len(scan["frames"]) == 3 and not scan["problems"]
    cal = execute("calibration.run", {"frames": scan["frames"], "output_dir": str(tmp_path / "cal")}, {}, Ctx())
    stack = execute("stacking.stack", {"images": cal["calibrated"], "output": str(tmp_path / "s.fits")}, {}, Ctx())
    assert fits.getdata(stack["stack"]).shape == (64, 80)
    inputs = {"images": cal["calibrated"], "target_xy": [30, 20], "comps_xy": [[60, 45]]}
    lc = execute("photometry.light_curve", inputs, {}, Ctx())["light_curve"]
    assert np.all(np.isfinite(lc["rel_flux"]))


def test_compressed_fz(tmp_path):
    rng = np.random.default_rng(2)
    (tmp_path / "lights").mkdir()
    for i in range(3):
        h = fits.Header({"IMAGETYP": "Light Frame", "EXPTIME": 10.0, "DATE-OBS": f"2025-01-01T20:0{i}:00"})
        hdus = [fits.PrimaryHDU(), fits.CompImageHDU(frame(i, rng).astype(np.float32), h)]
        fits.HDUList(hdus).writeto(tmp_path / "lights" / f"l{i}.fits.fz")
    scan = execute("calibration.scan", {"folder": str(tmp_path)}, {}, Ctx())
    cal = execute("calibration.run", {"frames": scan["frames"], "output_dir": str(tmp_path / "cal")}, {}, Ctx())
    assert len(cal["calibrated"]) == 3


def test_no_time_in_the_files(tmp_path):
    """A light curve against the frame number instead of an error; no AAVSO lines without times."""
    rng = np.random.default_rng(3)
    paths = []
    for i in range(3):
        p = tmp_path / f"n{i}.fits"
        fits.PrimaryHDU(frame(i, rng).astype(np.float32)).writeto(p)
        paths.append(str(p))
    lc = execute("photometry.light_curve", {"images": paths, "target_xy": [30, 20], "comps_xy": [[60, 45]]}, {}, Ctx())
    lc = lc["light_curve"]
    assert lc["time_scale"] == "frame number" and lc["time"] == [0.0, 1.0, 2.0]
    from astrowb.photometry.export import aavso_extended

    text = aavso_extended(lc, star_name="X", obscode="ABC", filt="V", comp_mags=[12.0])
    assert not [line for line in text.splitlines() if not line.startswith("#")]


def test_ragged_csv_rows_and_wrong_files(qtbot, tmp_path):
    """A CSV row longer than its header; a picture saved under a name matplotlib cannot write; a file that is not
    a project: no crash, and the open project stays usable."""
    from astrowb.timeseries import surveys

    rows = surveys._rows("time,flux\n1.0,2.0,extra,cells\n2.0,3.0\n")
    assert rows == [{"time": "1.0", "flux": "2.0"}, {"time": "2.0", "flux": "3.0"}]

    from matplotlib.figure import Figure

    from astrowb.ui.plot.export import save_publication

    fig = Figure()
    fig.add_subplot().plot([0, 1])
    assert save_publication(fig, tmp_path / "plot.fits").endswith("plot.fits.png")
    assert (tmp_path / "plot.fits.png").stat().st_size > 1000

    from PySide6.QtWidgets import QMessageBox

    from astrowb.settings import Settings
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    shown = []
    QMessageBox.warning, saved = (lambda *a, **k: shown.append(a[1])), QMessageBox.warning
    try:
        assert win.open_project(tmp_path / "p.astroproj")
        assert win.open_project(tmp_path / "plot.fits.png") is False and shown == ["Cannot open project"]
        win.engine.project.add_file(tmp_path / "plot.fits.png", "image")  # the first project still works
    finally:
        QMessageBox.warning = saved
        win.engine.shutdown()


def test_wrong_files_give_a_message(tmp_path):
    from astrowb.display import save_picture
    from astrowb.models.data import read_model_curve

    data = np.random.default_rng(0).normal(100, 5, (40, 50)).astype(np.float32)
    assert str(save_picture(tmp_path / "picture.fits", data)).endswith("picture.fits.png")
    bad = tmp_path / "frame.fits"
    fits.PrimaryHDU(data).writeto(bad)
    with pytest.raises(ValueError, match="two columns"):
        read_model_curve(bad)


def test_thumbnail_of_16_bit_camera_files_with_bzero(tmp_path):
    """The most common camera format (unsigned 16-bit with BZERO 32768) cannot be memory-mapped; its thumbnail
    was never drawn."""
    from astrowb.io.fits import thumbnail

    data = (np.arange(256 * 300) % 60000).astype(np.uint16).reshape(256, 300)
    fits.PrimaryHDU(data).writeto(tmp_path / "u16.fits")
    assert "BZERO" in fits.getheader(tmp_path / "u16.fits")
    assert thumbnail(tmp_path / "u16.fits").shape == (52, 60)
    cube = np.stack([data, data, data]).astype(np.uint16)
    fits.PrimaryHDU(cube).writeto(tmp_path / "cube.fits")
    assert thumbnail(tmp_path / "cube.fits").shape == (52, 60)

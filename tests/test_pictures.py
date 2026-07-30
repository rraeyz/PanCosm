"""Ordinary pictures (a phone's JPEG, PNG, TIFF) open everywhere: converted once to FITS with the EXIF time and
exposure, upright on screen, colour as brightness."""

import numpy as np
import pytest
from astropy.io import fits
from PIL import Image

from astrowb.engine.steps import execute
from astrowb.io.bayer import fits_copy, fits_paths, read_picture


def phone_picture(path, when="2025:08:12 23:41:05", seconds=0.5, shift=0):
    rgb = np.full((60, 80, 3), 20, np.uint8)
    rgb[10 + shift : 13 + shift, 30:33] = (250, 240, 230)  # a star near the top of the picture
    rgb[45:48, 60 + shift : 63 + shift] = (200, 200, 200)
    im = Image.fromarray(rgb)
    exif = Image.Exif()
    exif[272] = "Phone X"
    ifd = exif.get_ifd(0x8769)
    ifd[36867], ifd[33434], ifd[34855] = when, seconds, 800
    im.save(path, exif=exif)


def test_jpeg_with_exif(tmp_path):
    p = tmp_path / "IMG_0001.jpg"
    phone_picture(p)
    data, h = read_picture(p, clock_utc_offset_h=3)
    assert data.shape == (60, 80) and h["EXPTIME"] == 0.5 and h["ISOSPEED"] == 800
    assert h["DATE-OBS"] == "2025-08-12T20:41:05" and h["INSTRUME"] == "Phone X" and h["LINEAR"] is False
    assert 47 <= np.argmax(data[:, 31]) <= 49  # the top of the picture is the top on screen (FITS rows go up)


@pytest.mark.parametrize("name", ["a.png", "a.tif", "a.bmp"])
def test_other_formats(tmp_path, name):
    p = tmp_path / name
    a = (np.arange(60 * 80) % 4096).astype(np.uint16).reshape(60, 80)
    if name.endswith(".tif"):
        import tifffile

        tifffile.imwrite(p, np.dstack([a, a, a]))  # 16-bit colour TIFF, as some programs write
    elif name.endswith(".png"):
        Image.fromarray(a.astype(np.uint16)).save(p)
    else:
        Image.fromarray((a % 256).astype(np.uint8)).save(p)
    data, h = read_picture(p)
    assert data.shape == (60, 80) and np.isfinite(data).all()
    assert h["LINEAR"] == (not name.endswith(".bmp"))


def test_fits_copy_is_made_once_and_kept(tmp_path):
    p = tmp_path / "IMG_0001.jpg"
    phone_picture(p)
    f = fits_copy(p)
    assert f.parent.name == "fits_from_raw" and fits.getheader(f)["EXPTIME"] == 0.5
    mtime = f.stat().st_mtime
    assert fits_copy(p) == f and f.stat().st_mtime == mtime
    assert fits_copy(f) == f  # FITS stays as it is
    (tmp_path / "broken.jpg").write_text("not a picture")
    with pytest.warns(UserWarning, match="broken.jpg"):
        assert fits_paths([p, tmp_path / "broken.jpg"]) == [str(f)]


def test_phone_night_calibrates_and_stacks(tmp_path):
    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    night = tmp_path / "night"
    (night / "lights").mkdir(parents=True)
    for i in range(4):
        phone_picture(night / "lights" / f"IMG_{i:04d}.jpg", when=f"2025:08:12 23:4{i}:05", shift=i % 2)
    out = execute("calibration.scan", {"folder": str(night)}, {}, Ctx())
    assert out["raw_converted"] == 4 and sorted({f["kind"] for f in out["frames"]}) == ["light"]
    cal = execute("calibration.run", {"frames": out["frames"], "output_dir": str(tmp_path / "cal")}, {}, Ctx())
    stack = execute("stacking.stack", {"images": cal["calibrated"], "output": str(tmp_path / "s.fits")}, {}, Ctx())
    assert fits.getdata(stack["stack"]).shape == (60, 80)


def test_main_window_and_photometry_open_pictures(qtbot, tmp_path):
    from astrowb.settings import Settings
    from astrowb.ui.main_window import MainWindow

    paths = []
    for i in range(3):
        p = tmp_path / f"IMG_{i:04d}.jpg"
        phone_picture(p, when=f"2025:08:12 23:4{i}:05")
        paths.append(str(p))
    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    try:
        assert win.open_many(paths)
        assert win.current_path.suffix == ".fits" and win.viewer.data.shape == (60, 80)
        win.photometry_page.set_images(paths)
        assert all(p.endswith(".fits") for p in win.photometry_page.images)
    finally:
        win.engine.shutdown()


def test_files_dropped_on_the_window_open(qtbot, tmp_path):
    from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
    from PySide6.QtGui import QDropEvent

    from astrowb.settings import Settings
    from astrowb.ui.main_window import MainWindow

    p = tmp_path / "IMG_0001.jpg"
    phone_picture(p)
    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    try:
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(p)), QUrl.fromLocalFile(str(tmp_path / "night.astroproj"))])
        win.dropEvent(QDropEvent(QPointF(10, 10), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier))
        assert win.current_path.name == "IMG_0001.fits" and win.engine.project is not None
    finally:
        win.engine.shutdown()


def test_previews_next_to_fits_frames_are_not_frames(tmp_path):
    """PNG / JPEG exports in a folder of FITS frames stay out of the calibration; a folder of pictures only
    (a phone's night) is converted."""
    from astrowb.io.bayer import convert_raw_folder

    (tmp_path / "night").mkdir()
    fits.PrimaryHDU(np.zeros((10, 10), np.float32), fits.Header({"IMAGETYP": "Light Frame"})).writeto(
        tmp_path / "night" / "l1.fits"
    )
    phone_picture(tmp_path / "night" / "l1.png")
    assert convert_raw_folder(tmp_path / "night") == ([], [])
    (tmp_path / "phone").mkdir()
    phone_picture(tmp_path / "phone" / "IMG_0001.jpg")
    assert len(convert_raw_folder(tmp_path / "phone")[0]) == 1

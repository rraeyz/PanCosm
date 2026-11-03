"""Display levels, colour maps, picture export, header editing and blinking."""

import numpy as np
import pytest
from astropy.io import fits

from astrowb import display
from astrowb.io import fits as fitsio
from astrowb.settings import Settings


def test_levels_colours_and_inversion():
    a = np.linspace(0, 100, 101, dtype=np.float32).reshape(1, 101)
    pic = display.render(a, limits=(20, 80))
    assert pic[0, 10] == 0 and pic[0, 90] == 255 and pic[0, 50] == pytest.approx(128, abs=2)
    assert display.render(a, limits=(20, 80), invert=True)[0, 10] == 255
    rgb = display.render(a, limits=(20, 80), cmap="heat")
    assert rgb.shape == (1, 101, 3) and tuple(rgb[0, 0]) == (0, 0, 0)
    for name in display.COLOUR_MAPS:
        t = display.colour_table(name, invert=True)
        assert t is None or t.shape == (256, 3)
    b = np.arange(6.0).reshape(2, 3)
    pic = display.render(b, interval="minmax")  # the last FITS row is the top row on screen
    assert pic[0, 2] == 255 and pic[1, 0] == 0


def test_save_picture(tmp_path):
    from PIL import Image

    a = np.random.default_rng(0).random((20, 30)).astype(np.float32)
    for name in ("p.png", "p.jpg"):
        display.save_picture(tmp_path / name, a, cmap="viridis")
        assert Image.open(tmp_path / name).size == (30, 20)
    import tifffile

    display.save_picture(tmp_path / "d.tif", a)
    assert np.array_equal(tifffile.imread(tmp_path / "d.tif"), np.flipud(a))  # the data, image orientation


def test_header_changes_are_written_to_a_copy(fits_file, tmp_path):
    assert fitsio.parse_value("T") is True and fitsio.parse_value("12") == 12 and fitsio.parse_value("1.5") == 1.5
    assert fitsio.parse_value("M 42") == "M 42"
    out = fitsio.save_as(fits_file, tmp_path / "c.fits", set_cards={"filter": ["V", "Johnson V"]}, delete=["OBJECT"])
    h = fits.getheader(out)
    assert h["FILTER"] == "V" and h.comments["FILTER"] == "Johnson V" and "OBJECT" not in h
    assert fits.getheader(fits_file)["OBJECT"] == "TEST"  # the original is never changed
    assert np.array_equal(fits.getdata(out), fits.getdata(fits_file))
    with pytest.raises(ValueError, match="ASCII"):
        fitsio.save_as(fits_file, tmp_path / "e.fits", set_cards={"SITE": ["Güneş", ""]})
    with pytest.raises(ValueError, match="NAXIS1"):
        fitsio.save_as(fits_file, tmp_path / "d.fits", set_cards={"NAXIS1": [3, ""]})


def test_header_tab_and_menus(qtbot, tmp_path, fits_file):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path / "s"))
    qtbot.addWidget(win)
    try:
        win.open_fits(fits_file)
        page = win.image_page
        assert page.set_keyword("observer", "A. Gozlemci", "who") and not page.set_keyword("BITPIX", 8)
        assert not page.set_keyword("SITE", "Antalya Güneş")  # FITS headers are ASCII
        page.delete_keyword("OBJECT")
        assert page.header_save.isEnabled()
        keys = [page.header_table.item(i, 0).text() for i in range(page.header_table.rowCount())]
        assert "OBSERVER" in keys and "OBJECT" not in keys
        task = win.save_header_changes(dict(page.header_set), list(page.header_delete), tmp_path / "h.fits")
        task.result(60)
        qtbot.waitUntil(lambda: win.current_path == tmp_path / "h.fits", timeout=10000)
        assert fits.getheader(tmp_path / "h.fits")["OBSERVER"] == "A. Gozlemci"
        assert not page.header_save.isEnabled()  # the new file is open, nothing pending
        dlg = win.levels_dialog()
        dlg.black.setValue(990.0)
        dlg.white.setValue(1100.0)
        dlg.cmap.setCurrentIndex(dlg.cmap.findData("heat"))
        assert win.viewer.limits == (990.0, 1100.0) and win.viewer.cmap == "heat"
        dlg.automatic()
        assert win.viewer.limits is None
        assert win.save_picture_dialog(tmp_path / "shown.png").exists()
    finally:
        win.engine.shutdown()


def test_blink_aligns_the_frames(qtbot, tmp_path):
    from astrowb.ui.blink_dialog import BlinkDialog

    yy, xx = np.mgrid[:100, :120]
    paths = []
    for i, (dx, dy) in enumerate(((0, 0), (5, -3), (-4, 6))):
        img = 100 + sum(
            3000 * np.exp(-((xx - x - dx) ** 2 + (yy - y - dy) ** 2) / 4.0)
            for x, y in ((30, 40), (80, 25), (60, 70), (95, 85))
        )
        h = fits.Header({"DATE-OBS": f"2026-11-15T20:0{i}:00"})
        fits.PrimaryHDU(img.astype(np.float32), h).writeto(tmp_path / f"b{i}.fits")
        paths.append(tmp_path / f"b{i}.fits")
    dlg = BlinkDialog()
    qtbot.addWidget(dlg)
    dlg.set_images([str(p) for p in paths])
    for i in (1, 2):
        dlg.show_frame(i)
        assert np.unravel_index(np.argmax(dlg.viewer.data[30:50, 20:40]), (20, 20)) == (10, 10)  # star back at 30, 40
    dlg.play.setChecked(True)
    assert dlg.timer.isActive() and dlg.label.text().startswith("3 / 3")
    dlg.close()
    assert not dlg.timer.isActive()

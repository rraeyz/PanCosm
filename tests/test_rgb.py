"""Colour image from three filters: aligned, star colours kept."""

import numpy as np
from astropy.io import fits

from astrowb.engine.steps import execute
from astrowb.io.process import colour_image


def field(dx=0.0, dy=0.0, weights=(1.0, 1.0)):
    yy, xx = np.mgrid[:90, :120]
    img = np.full(xx.shape, 100.0)
    for (x, y), w in zip(((40.0, 30.0), (80.0, 60.0)), weights, strict=True):
        img += 5000 * w * np.exp(-((xx - x - dx) ** 2 + (yy - y - dy) ** 2) / 4.5)
    return img + np.random.default_rng(abs(int(10 * dx + 37))).normal(0, 3, img.shape)


def test_colour_image_aligns_and_keeps_colours():
    red, green, blue = field(weights=(1.0, 0.2)), field(3.0, -2.0, (0.6, 0.6)), field(-4.0, 1.0, (0.2, 1.0))
    rgb = colour_image(red, green, blue)
    assert rgb.shape == (90, 120, 3) and rgb.dtype == np.uint8
    y_red, y_blue = 89 - 30, 89 - 60  # flipped: row 0 is the top of the picture
    r_star, b_star = rgb[y_red, 40].astype(int), rgb[y_blue, 80].astype(int)
    assert r_star[0] > r_star[2] + 50 and b_star[2] > b_star[0] + 50  # a red and a blue star
    for c in range(3):  # aligned: each channel peaks at the same place
        assert np.unravel_index(np.argmax(rgb[:, :, c] * (np.arange(120) < 60)), (90, 120)) == (y_red, 40)


def test_rgb_step_writes_a_png(tmp_path):
    class Ctx:
        def progress(self, *a):
            pass

    paths = {}
    for k, img in zip(("red", "green", "blue"), (field(), field(1, 1), field(-1, 2)), strict=True):
        fits.PrimaryHDU(img.astype(np.float32)).writeto(tmp_path / f"{k}.fits")
        paths[k] = str(tmp_path / f"{k}.fits")
    out = execute("image.rgb", paths | {"output": str(tmp_path / "c.png")}, {}, Ctx())["rgb"]
    from matplotlib.image import imread

    assert imread(out).shape[:2] == (90, 120)


def test_colour_image_from_the_image_menu(qtbot, tmp_path):
    from astrowb.settings import Settings
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    try:
        paths = []
        for k in ("r", "g", "b"):
            fits.PrimaryHDU(field().astype(np.float32)).writeto(tmp_path / f"{k}.fits")
            paths.append(str(tmp_path / f"{k}.fits"))
        win.colour_dialog(paths, str(tmp_path / "c.png"))
        qtbot.waitUntil(lambda: getattr(win, "picture_dialog", None) is not None, timeout=60000)
        assert win.picture_dialog.windowTitle() == "c.png"
    finally:
        win.engine.shutdown()

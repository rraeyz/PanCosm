"""PLAN 4.8 item 15: no page is wider than the window at 960 x 700 (half of a 1920 screen) with a 10 pt font, in
any language, and no column inside a page scrolls sideways: a page that grows sideways hides its controls (the owner's
Calibrate page was cut off on the right). Long button rows go into grids, long labels wrap, columns stack.

Measured with DejaVu Sans, the wide default font of many Linux desktops, so the result does not depend on the fonts
of the machine running the tests; on Linux only, where the off-screen platform has the desktop's 96 dpi (Windows'
off-screen platform reports another resolution and gives sizes no real window has)."""

import sys

import pytest

from astrowb.settings import Settings
from astrowb.ui import i18n, theme


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="sizes measured on Linux (see the module text)")
@pytest.mark.parametrize("look", ["dark", "light"])
@pytest.mark.parametrize("lang", ["en", "tr", "de", "es"])
def test_every_page_fits_a_small_window(qapp, qtbot, tmp_path, lang, look):
    from PySide6.QtGui import QFont, QFontDatabase
    from PySide6.QtWidgets import QScrollArea

    from astrowb.ui.main_window import MainWindow

    if "DejaVu Sans" not in QFontDatabase.families():
        pytest.skip("DejaVu Sans is not installed")
    old_font = qapp.font()
    qapp.setFont(QFont("DejaVu Sans", 10))
    theme.apply(qapp, look)  # as the application starts: the theme's padding makes buttons wider
    translators = i18n.install(qapp, lang)
    settings = Settings(tmp_path)
    settings.set("ui.language", lang)
    win = MainWindow(settings)
    qtbot.addWidget(win)
    try:
        win.resize(960, 700)
        win.show()
        too_wide = {}
        for attr in list(win._placeholders):
            page = getattr(win, attr)
            frame = win._frames[page]
            win.pages.setCurrentWidget(frame)
            qapp.processEvents()
            qapp.processEvents()  # columns stacked on a narrow window lay out again
            need, have = page.minimumSizeHint().width(), frame.viewport().width()
            sideways = [
                a for a in page.findChildren(QScrollArea) if a.isVisible() and a.horizontalScrollBar().isVisible()
            ]
            if need > have or sideways:
                too_wide[attr] = (need, have, len(sideways))
        assert not too_wide, too_wide
    finally:
        win.engine.shutdown()
        for t in translators:
            qapp.removeTranslator(t)
        qapp.setFont(old_font)

"""Look and first run: themes apply to widgets and plots; the welcome dialog runs once and is English."""

import matplotlib as mpl

from astrowb.settings import Settings
from astrowb.ui import theme
from astrowb.ui.welcome import WelcomeDialog, first_run


def test_themes_apply(qapp):
    for name in theme.THEMES:
        c = theme.apply(qapp, name)
        assert c["window"] in qapp.styleSheet() and mpl.rcParams["axes.facecolor"] == c["panel"]
        assert mpl.rcParams["savefig.facecolor"] == "auto"  # Save = as on screen (print: Publication figure…)
    assert theme.colors("night") == theme.colors("dark")  # the removed red theme falls back to dark
    theme.apply(qapp, "dark")


def test_first_run_once(qapp, qtbot, tmp_path):
    settings = Settings(tmp_path)

    class Auto(WelcomeDialog):
        def exec(self):  # the user picks Turkish, CPU, light look and presses Start
            self.language.setCurrentIndex(self.language.findData("tr"))
            self.device.setCurrentIndex(self.device.findData("cpu"))
            self.look.setCurrentIndex(self.look.findData("light"))
            return 1

    chosen = first_run(qapp, settings, Auto)
    assert chosen == {"ui.language": "tr", "compute.device": "cpu", "ui.theme": "light", "time.auto_refresh": True}
    assert Settings(tmp_path).get("ui.first_run_done") is True
    assert first_run(qapp, settings, Auto) is None  # never again
    dlg = WelcomeDialog()
    qtbot.addWidget(dlg)
    assert dlg.windowTitle().startswith("Welcome")  # the first screen is English
    theme.apply(qapp, "dark")


def test_settings_menu_theme(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    try:
        win.set_theme("light")
        assert win.settings.get("ui.theme") == "light"
        assert theme.colors("light")["window"] in qtbot_app_style()
    finally:
        win.set_theme("dark")
        win.engine.shutdown()


def qtbot_app_style():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance().styleSheet()


def test_quick_tour(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    win.resize(1200, 800)
    win.show()
    try:
        tour = win.start_tour()
        assert win.settings.get("ui.tour_done") is True and tour.isVisible()
        rects = []
        for i in range(len(tour.steps)):
            rects.append(tour._rect())
            assert tour.bubble.geometry().intersects(tour.rect())  # the text is always on screen
            assert tour.text.text()
            if i < len(tour.steps) - 1:
                tour.advance()
        assert rects[0] is None and all(r is not None for r in rects[1:])  # every later step highlights something
        assert tour.next.text() in ("Done", "Bitti")
        tour.advance()
        assert tour.finished
    finally:
        win.engine.shutdown()

"""Screenshots for the Guide, made from the practice data (run again after UI changes).

    QT_QPA_PLATFORM=offscreen python tools/guide_screenshots.py [language ...]
writes src/astrowb/resources/guide/images/<language>/: the first-night exercise (first-night-*.png) and one
picture of every area window as it opens (window-<area>.jpg), dark look, 1000 px wide, every interface language
by default, so each Guide shows the interface in its own language. Each picture is of the area's own window
(interface I7.3), not of the main window.
"""

import sys
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

OUT = Path(__file__).resolve().parents[1] / "src" / "astrowb" / "resources" / "guide" / "images"


def wait(app, condition, timeout=300):
    end = time.monotonic() + timeout
    while not condition():
        app.processEvents()
        if time.monotonic() > end:
            sys.exit("timed out")
        time.sleep(0.05)


def shot(app, win, out):
    win.resize(1366, 768)
    win.show()
    for _ in range(20):
        app.processEvents()
        time.sleep(0.02)
    picture = win.grab().scaledToWidth(1000, Qt.SmoothTransformation)
    picture.save(str(out), "JPEG" if out.suffix == ".jpg" else "PNG", 80)
    print("wrote", out)


def screenshots(app, lang, work, truth):
    from astrowb.settings import Settings
    from astrowb.ui import i18n
    from astrowb.ui.main_window import MainWindow

    translators = i18n.install(app, lang)
    settings = Settings(work / f"settings-{lang}")
    settings.set("ui.language", lang)
    win = MainWindow(settings)
    win.resize(1400, 860)
    win.show()
    out = OUT / lang
    out.mkdir(parents=True, exist_ok=True)
    try:
        win.show_workspace("calibrate")
        page = win.calibrate_page
        page.folder.setText(str(work / "raw"))
        page.output.setText(str(work / f"cal-{lang}"))
        win.scan_raw(str(work / "raw"))
        wait(app, lambda: page.table.rowCount() > 0)
        shot(app, win.area_windows["calibrate"], out / "first-night-calibrate.png")
        page._run()
        wait(app, lambda: bool(page.calibrated))
        win.show_workspace("photometry")
        ph = win.photometry_page
        ph.set_images(page.calibrated)
        ph._clicked(*truth["target_xy"])
        for c in truth["comps_xy"]:
            ph._clicked(*c)
        ph.coord.setText(f"{truth['ra']} {truth['dec']}")
        ph._measure()
        wait(app, lambda: ph.light_curve is not None)
        ph.kvw.setChecked(True)
        before = ph.result.text()
        ph._minimum()
        wait(app, lambda: ph.result.text() != before)
        shot(app, win.area_windows["photometry"], out / "first-night-photometry.png")
        win.show_workspace("automation")
        auto = win.automation_page
        auto.list.setCurrentRow(next(i for i, a in enumerate(auto.found) if Path(a["path"]).name.startswith("10-")))
        auto.edits["folder"].setText(str(work / "raw"))
        auto.edits["output_dir"].setText(str(work / f"cal2-{lang}"))
        auto.edits["target_xy"].setText(f"{truth['target_xy'][0]} {truth['target_xy'][1]}")
        shot(app, win.area_windows["automation"], out / "first-night-automation.png")
        win.open_fits(Path(page.calibrated[0]))  # the Images window with a calibrated frame of the night
        win.plan_page.add_target({"name": "Practice star", "ra": 31.04167, "dec": 46.68778, "source": "RA Dec"})
        computing = win.plan_page.status.text()
        win.plan_page._plan()
        wait(app, lambda: win.plan_page.status.text() not in (computing, win.plan_page.tr("Computing…")), 120)
        for key in win.WINDOWED:  # every window as it opens, with the night's data where the exercise made some
            win.show_workspace(key)
            shot(app, win.area_windows[key], out / f"window-{key}.jpg")
            win.area_windows[key].hide()
    finally:
        win.engine.shutdown()
        win.close()
        for t in translators:
            app.removeTranslator(t)


def main():
    from astrowb import sampledata
    from astrowb.ui import i18n, theme

    app = QApplication([])
    theme.apply(app, "dark")
    work = Path(tempfile.mkdtemp())
    truth = sampledata.make(work)
    for lang in sys.argv[1:] or list(i18n.LANGUAGES):
        screenshots(app, lang, work, truth)


if __name__ == "__main__":
    main()
